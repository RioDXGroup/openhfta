! ================================================================================
! YTWCore1: OpenHFTA High Frequency Terrain Analysis Main Computation Engine
! ================================================================================
! Purpose: Computes the elevation-plane field pattern of HF antennas over terrain
!          using ray tracing, geometrical optics, UTD diffraction, and Fresnel reflection
!
! Theory: This routine implements the HFTA terrain-analysis algorithm described in:
!         - ARRL HFTA Operating Instructions (Dean Straw, N6BV)
!           http://arrl.org/files/file/Product%20Notes/Antenna%20Book/hfta.pdf
!         - N6BV, Terrain Assessment for HF Contesting (Sea-Pac 2014)
!           https://seapac.org/seminars/2014/sea-pac2014-n6bv-Terrain%20Assessment.pdf
!         - Kouyoumjian & Pathak, Uniform Geometrical Theory of Diffraction (1974)
!
! Algorithm Overview:
! 1. Ray tracing scan from -55 deg to +35 deg in 0.25 deg steps; final output is 0.25 deg to 35 deg
! 2. Thin the terrain profile, mark diffraction vertices, and trace rays over terrain
! 3. Apply GO (geometrical optics) for direct and specular reflection paths
! 4. Apply UTD (Uniform Geometrical Theory of Diffraction) for terrain edge diffraction
! 5. Evaluate Fresnel reflection coefficients for lossy ground interaction
! 6. Sum all field contributions coherently across antenna array elements
! 7. Sum complex fields, convert to magnitudes, smooth, and convert to dB
!
! Input / Work Parameters:
!   DG0_in(0:150)      - Terrain distance profile [feet]; may receive the far endpoint
!   HG0_in(0:150)      - Terrain height profile [feet ASL]; paired far height may be appended
!   HantFeetIn(0:3)    - Antenna heights [feet] for up to 4 stacked elements
!   FREQ_MHZ_in        - Operating frequency [MHz]
!   SOIL_EPSR_in       - Soil relative permittivity for Fresnel reflection
!   SOIL_COND_PARAM_in - Soil conductivity [S/m] for complex permittivity
!   AntPatternType     - Antenna pattern types (HFTA GUI mapping):
!                        1=Dipole, 2=2-Ele, 3=3-Ele, 4=4-Ele,
!                        5=5-Ele, 6=6-Ele, 7=8-Ele
!   DiffractionDisable - Diffraction analysis control flag (1=disable, 0=enable)
!   DebugEnable_in     - Debug file output enable (1=on, 0=off)
!   DebugExitAngle_in  - Specific exit angle for detailed debug output [degrees]
!   AntPhase(0:3)      - Phase settings: 1=0°, -1=180° for each antenna element
!
! Output Parameters:
!   Pattern_dB(0:139)  - Elevation pattern in dB; 140 points at 0.25° resolution
!                        Covers 0.25° to 35°; idx = (angle_deg * 4) - 1
!                        Final output uses 0.25 deg to 35 deg; FOM analyzes 1 deg to 35 deg
!                        Relative pattern with antenna scale and terrain effects
!
! Key Physical Constants Used:
!   LAMBDA_FT = 983.5712/f_MHz [feet], k = 2π/λ [rad/ft], f in MHz
!   FRESNEL uses ABS(outgoing ray angle) in Gh=(sin a-sqrt(eps-cos^2 a))/(sin a+sqrt(...))
!   with eps = eps' - j*sigma/(omega*eps0); horizontal-polarization coefficient
!   UTD diffraction uses scalar straight-wedge terms with one L_waves per YUTD call
!
! ================================================================================
subroutine YTWCore1 (DG0_in, HG0_in, HantFeetIn, FREQ_MHZ_in, SOIL_EPSR_in, SOIL_COND_PARAM_in, AntPatternType, DiffractionDisable, DebugEnable_in, DebugExitAngle_in, Pattern_dB, AntPhase) !1
!DEC$ ATTRIBUTES DLLEXPORT::YTWCore1
    implicit none
    real*4 DG0_in(0:150), HG0_in(0:150), HantFeetIn(0:3), FREQ_MHZ_in, SOIL_EPSR_in, SOIL_COND_PARAM_in
    integer*2 AntPatternType, DiffractionDisable, DebugEnable_in
    real*4 DebugExitAngle_in, Pattern_dB(0:139)
    integer*2 AntPhase(0:3)

    logical MadeHit, MadeItOut, UnusedWasAboveTerrain
    integer*2 AngleIdxByElemLaunch(1:4,-220:180), IsDiffPoint(1:200)
    integer*2 NDiffPoints, NPointsSmoothed_i2, M_i2, NSmoothedPts_i2, RDPoint_i2
    integer*4 InitAngleIdx, Ipt, M, KeepIdx, SweepStepIdx, AngleIdx, DebugEnable, DebugMode, ProcessFlag, ScanIdx, LastPointIdx, IptDbg, NElements
    integer*4 NPointsSmoothed, ElemIdx, NSteps, NDiffPoints_i4, LaunchIdxQ, RDHitIdx, FoundRD, IterCount, AdjustSign, CoarseAdjustMode, AngleIdx_0_180, AngleIdx_1_180, SmoothIdx, UnusedScanStepIdx
    real*4 RayHeightAtAngle(-220:180), SlantSegFt(-220:180), ElemPatternAmp(1:4,-220:180), ElemPhase(1:4,-220:180), PatternMag(0:181), UnusedPatternSmoothed(0:181), HantFeetAbs(1:4)
    real*4 PatternBeamwidthDeg, AntPatternGainFactor, DebugExitAngle, LAMBDA_OVER_8_FT, Slpe1, Slpe2, NElements_f, InvSqrtN, ASlp2, ASlp1, SegLenFt
    real*4 LaunchAngle, RayHeightCurrent, HtRay, PhaseToM, AntEdgeDistWaves, ElemGain, PHRStepNeg0p25, PHR, PhiP, Incl, TotSlantFt, PHRout, ReflPhase
    real*4 ReflAmp, HG_at_M, PHRF, PhaseWork, OutputField, UTD_OutPhase, UTD_OutMag, UnusedUTDZero, FinalPhase, AngleIdx_f, AngleOutRad, RayHeightPrev, ReflGainSaved
    real*4 ElemPatternAmp_curr, SegmentAngleRad, ReflectPointHeightFt, ReflectPointDistFt, ReflectOffset, SegmentSlope, ReflGain, RayHeightPred, LastRayAngleBeforeRefl, PhaseAccumRad, RayHeight, RayAngle, LastHeightError
    real*4 RayAngle0, SegAngle, HeightAtIntersect, AlongSegToIntersect, SegSlope, SlantSegLen, NextRayHeight, SlopeAtTarget, AngleAdjust, PhaseToRDEdgeRad, TotalSlantWaves, DirectSlantToRDPoint, UnusedSlantToIptIfDirect, AngleOutRad_RD
    real*4 HtRayOut, FinalPhaseGO

    complex*8 E_total_tmp(0:181), E_diffAccum(0:181), E_goAccum(0:181)

    integer*2 DiffPtIdx(1:200), EdgePairUsed(1:200, 1:200), NCountDiff(0:180), TotalDiffCount
    real*4 DiffPh0(1:4, 1:200), FAngle(1:4, 1:200)
    common /Globals/ DiffPtIdx, EdgePairUsed, NCountDiff, TotalDiffCount, DiffPh0, FAngle

    real*4 DG(0:150), HG(0:150), FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE
    common /Params/ DG, HG, FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    real*4, external :: ATN4

    integer, parameter :: I2 = selected_int_kind(4)

    do InitAngleIdx = -220, 180  !77
        RayHeightAtAngle(InitAngleIdx) = 0.0  ! Initialize ray heights for elevation scan  !78
        SlantSegFt(InitAngleIdx) = 0.0  ! Reset slant distances for each angle  !79
    end do  !80
    do Ipt = 0, 150  !81
        DG(Ipt) = 0.0  !82
        HG(Ipt) = 0.0  !83
    end do  !84
    do M = 1, 4  !85
        do KeepIdx = -220, 180  !86
            AngleIdxByElemLaunch(M, KeepIdx) = 0  !87
            ElemPatternAmp(M, KeepIdx) = 0.0  !88
            ElemPhase(M, KeepIdx) = 0.0  !89
        end do  !90
    end do  !91
    do M = 1, 4  !92
        do KeepIdx = 1, 200  !93
            FAngle(M, KeepIdx) = 0.0  !94
            DiffPh0(M, KeepIdx) = 0.0  !95
        end do  !96
    end do  !97
    do InitAngleIdx = 0, 181  !98
        E_total_tmp(InitAngleIdx) = CMPLX(0.0, 0.0)  !99
        E_diffAccum(InitAngleIdx) = CMPLX(0.0, 0.0)  !100
        E_goAccum(InitAngleIdx) = CMPLX(0.0, 0.0)  !101
        PatternMag(InitAngleIdx) = 0.0  !102
        UnusedPatternSmoothed(InitAngleIdx) = 0.0  !103
    end do  !104
    do KeepIdx = 1, 4  !105
        HantFeetAbs(KeepIdx) = 0.0  !106
    end do  !107
    do KeepIdx = 1, 200  !108
        IsDiffPoint(KeepIdx) = 0  !109
        DiffPtIdx(KeepIdx) = 0  !110
        do SweepStepIdx = 1, 200  !111
            EdgePairUsed(KeepIdx, SweepStepIdx) = 0  !112
        end do  !113
    end do  !114
    !do KeepIdx = 1, 180  !115
    !    SHORT_ARRAY_10013386(KeepIdx) = 0  !116
    !end do  !117
    do KeepIdx = 0, 180  !118
        NCountDiff(KeepIdx) = 0  !119
    end do  !120

    do M = 1, 140  !122
        Pattern_dB(M - 1) = 0.0  !123
    end do  !124
    AngleIdx = 0  !125
    !INT_1001221c = 0  !126
    !FLOAT_10012218 = 0.0  !127

    ! Convert input antenna heights to working array with absolute values
    ! The element-height calculation uses the magnitude of each height
    HantFeetAbs(1) = ABS(HantFeetIn(0))  !131
    HantFeetAbs(2) = ABS(HantFeetIn(1))  !132
    HantFeetAbs(3) = ABS(HantFeetIn(2))  !133
    HantFeetAbs(4) = ABS(HantFeetIn(3))  !134

    ! Store input parameters in common block variables for global access
    ! FREQ_MHZ: Operating frequency in MHz, used throughout for wavelength calculations
    ! SOIL_EPSR/SOIL_COND_PARAM: soil permittivity and conductivity for Fresnel reflection
    FREQ_MHZ = FREQ_MHZ_in  !136
    SOIL_EPSR = SOIL_EPSR_in  !137
    SOIL_COND_PARAM = SOIL_COND_PARAM_in  !138

    ! Antenna pattern parameters based on type selection (HFTA GUI mapping)
    ! Sets element elevation beamwidth (PatternBeamwidthDeg) and an
    ! element field-amplitude scale (AntPatternGainFactor), not a power scale.
    ! 1=Dipole, 2=2-Ele, 3=3-Ele, 4=4-Ele, 5=5-Ele, 6=6-Ele, 7=8-Ele
    if (AntPatternType == 1) then  !139
        PatternBeamwidthDeg = 90.0  !140
        AntPatternGainFactor = 1.281  !141
    else if (AntPatternType == 2) then  !142
        PatternBeamwidthDeg = 70.0  !143
        AntPatternGainFactor = 1.884  !144
    else if (AntPatternType == 3) then  !145
        PatternBeamwidthDeg = 65.0  !146
        AntPatternGainFactor = 2.239  !147
    else if (AntPatternType == 4) then  !148
        PatternBeamwidthDeg = 60.0  !149
        AntPatternGainFactor = 2.661  !150
    else if (AntPatternType == 5) then  !151
        PatternBeamwidthDeg = 55.0  !152
        AntPatternGainFactor = 2.985  !153
    else if (AntPatternType == 6) then  !154
        PatternBeamwidthDeg = 50.0  !155
        AntPatternGainFactor = 3.548  !156
    else if (AntPatternType == 7) then  !157
        PatternBeamwidthDeg = 45.0  !158
        AntPatternGainFactor = 3.981  !159
    end if

    DebugEnable = DebugEnable_in  !161
    DebugExitAngle = DebugExitAngle_in  !162
    if (DebugExitAngle_in > 0.0) then  !163
        DebugMode = 0
    end if

    ! Initialize fundamental electromagnetic and mathematical constants
    ! Used for ray tracing, field calc, and conversions
    ! PI = π, TWO_PI = 2π for angles; DEG2RAD = π/180 for conversions
    PI = 3.141593  !169
    TWO_PI = PI*2.0  !170

    ! UTD magnitude cutoff used by single-edge/RD and second-edge cascades
    ! Single-edge and RD paths test the current coefficient before tracing out
    ! DIFFDIFF/DRD do not cut off the first-edge coefficient here
    ! Their second-edge coefficient, and DRD's final field, use this gate
    ! Value 0.1 is a field-amplitude cutoff (about -20 dB in field magnitude)
    UTD_MAG_THRESHOLD = 0.1  !172

    DEG2RAD = PI/180.0 !174

    HALF_PI = PI/2  !176

    EARTH_RADIUS_FT = 20926000.0  !178

    ! Initialize processing control variables
    ! ProcessFlag is initialized before the later DRD call condition
    ! Main ray tracing, single-edge diffraction, and DIFFDIFF run with value 1
    ! The later DRD branch requires ProcessFlag == 0
    ProcessFlag = 1  !185

    if (DebugEnable == 1) then  !187
        ! Open debug output files for detailed ray tracing analysis
        ! TEST1.PRN: Terrain profile and diffraction point analysis
        OPEN(UNIT=3, FILE='TEST1.PRN', ACTION='WRITE')  !190
        ! TEST4.PRN: Detailed ray path calculations and UTD results
        OPEN(UNIT=4, FILE='TEST4.PRN', ACTION='WRITE')  !193
        ! TEST5.PRN: Terrain smoothing/profile thinning diagnostics
        OPEN(UNIT=5, FILE='TEST5.PRN', ACTION='WRITE')  !196
    end if

    ! Calculate fundamental electromagnetic parameters from frequency
    ! LAMBDA_FT = 983.5712/f_MHz gives wavelength in feet for this core
    LAMBDA_FT = 983.5712 / FREQ_MHZ  !203
    ! Wavenumber k = 2π/λ [radians per foot] - fundamental for phase calculations
    ! All path lengths multiplied by k give electrical path length in radians
    k = (PI * 2.0) / LAMBDA_FT !206
    ! λ/8 vertical threshold for terrain-profile thinning
    ! It compares height difference from the last kept point, not spacing
    LAMBDA_OVER_8_FT = LAMBDA_FT * 0.125  !210
    ! PATTERN_ELEV_NORM60_OVER_BW: Elevation angle normalization factor for antenna patterns
    PATTERN_ELEV_NORM60_OVER_BW = 60.0 / PatternBeamwidthDeg !212

    ! ========================================================================
    ! TERRAIN PROFILE PROCESSING AND SMOOTHING
    ! ========================================================================
    ! The smoothing pass keeps points that differ vertically by
    ! at least λ/8 from the last kept point, then appends an end point.
    ! This reduces closely spaced profile samples before the ray and
    ! diffraction passes while keeping lambda/8 height changes.

    ! Find the actual end of the terrain profile data
    ! Array is dimensioned 0:150 but actual profile may be shorter
    do ScanIdx = 2, 150  !220
        if (DG0_in(ScanIdx) == 0.0) then  !221
            exit
        end if
    end do
    ! Record the raw last point found by the zero-distance sentinel
    ! The working-profile test below may replace it with a 100000 ft endpoint
    LastPointIdx = ScanIdx - 1  !227
    KeepIdx = 2  !239
    DG(1) = DG0_in(1)  !240
    HG(1) = HG0_in(1)  !241
    DG(2) = DG0_in(2)  !242
    HG(2) = HG0_in(2)  !243
    if (DG(LastPointIdx) <= 99999.0) then  !244
        LastPointIdx = ScanIdx  !245
        DG0_in(ScanIdx) = 100000.0  !246
        HG0_in(LastPointIdx) = HG0_in(LastPointIdx - 1)  !249
    end if
    do M = 2, LastPointIdx + 1  !251
        ! Calculate adjacent raw slopes for the terrain-reduction pass
        ! In this thinning loop they are computed but not used by the test
        ! below, which depends only on height change from the last kept point.
        if (M > 1) then  !256
            Slpe1 = (HG0_in(M) - HG0_in(M-1)) / (DG0_in(M) - DG0_in(M-1))  !257
        end if
        if (M + 1 <= LastPointIdx) then  !259
            Slpe2 = ((HG0_in(M+1) - HG0_in(M)) / (DG0_in(M+1) - DG0_in(M)))  !260

            if (LAMBDA_OVER_8_FT <= ABS(HG0_in(M) - HG(KeepIdx))) then  !270
                ! Include this terrain point when the height change from the
                ! last kept profile point reaches λ/8. The next tests then
                ! work from the reduced terrain polyline.
                KeepIdx = KeepIdx + 1  !272
                DG(KeepIdx) = DG0_in(M)  !273
                HG(KeepIdx) = HG0_in(M) !274
            end if
        end if
    end do

    HG(KeepIdx + 1) = HG0_in(LastPointIdx)  !287
    DG(KeepIdx + 1) = DG0_in(LastPointIdx)  !288

    ! Debug output: log both raw and smoothed terrain profiles
    if (DebugEnable == 1) then  !290
        WRITE(5, *) 'Unsmoothed points'  !291
        DO SweepStepIdx = 1, LastPointIdx  !292
            WRITE(5, FMT='("N = ", I3, "  DG0 = ", F10.3, "  HG0 = ", F10.3)') &
                SweepStepIdx, DG0_in(SweepStepIdx), HG0_in(SweepStepIdx)
        END DO
        WRITE(5, *) 'Smoothed points'  !296
        DO IptDbg = 1, KeepIdx + 1  !297
            WRITE(5, FMT='("N = ", I3, "  DG = ", F10.3, "  HG = ", F10.3)') &
                IptDbg, DG(IptDbg), HG(IptDbg)
        END DO
        WRITE(5, *) '  '  !301
    end if

    NPointsSmoothed = KeepIdx + 1  !304

    ! ========================================================================
    ! ANTENNA ARRAY CONFIGURATION AND ELEMENT COUNT
    ! ========================================================================
    ! Determine the number of active antenna elements in the stacked array
    ! The antenna model supports up to 4 vertically stacked elements with independent heights and phases
    if (HantFeetAbs(2) == 0.0 .and. HantFeetAbs(3) == 0.0 .and. HantFeetAbs(4) == 0.0) then  !306
        NElements = 1  !307
    else if (HantFeetAbs(2) /= 0.0 .and. HantFeetAbs(3) == 0.0 .and. HantFeetAbs(4) == 0.0) then  !308
        NElements = 2  !309
    else if (HantFeetAbs(3) /= 0.0 .and. HantFeetAbs(4) == 0.0) then  !310
        NElements = 3
    else  !310
        NElements = 4  !311
    end if

    ! Field normalization by 1/sqrt(N) for stacked elements
    ! Scales each element before the coherent stack sum
    NElements_f = REAL(NElements)  !316
    InvSqrtN = 1.0 / SQRT(NElements_f)  !317
    ! Scale pattern by gain factor and normalization; affects overall field strength
    ARRAY_PATTERN_SCALE = AntPatternGainFactor * InvSqrtN  !319

    ! ========================================================================
    ! DIFFRACTION EDGE DETECTION AND UTD ANALYSIS
    ! ========================================================================
    ! This section identifies terrain vertices for the UTD calculation
    ! by testing adjacent slope changes and geometry limits.
    ! Selected points are stored in DiffPtIdx for the diffraction passes.
    !
    ! References:
    ! - Keller, J.B., "Geometrical Theory of Diffraction" (1962)
    ! - Kouyoumjian & Pathak, "Uniform Geometrical Theory of Diffraction" (1974)

    ! Enable diffraction if not disabled; flag controls diffraction analysis
    if (DiffractionDisable /= 1) then  !322
        NDiffPoints = 0  !338
        TotalDiffCount = 0  !339

        ! ====================================================================
        ! TERRAIN FEATURE ANALYSIS FOR DIFFRACTION POINTS
        ! ====================================================================
        ! Scan terrain profile for slope changes treated as diffraction
        ! candidates for the diffraction model

        do M = 1, NPointsSmoothed  !341
            if (M == 1) then  !342
                ! Compute the first-point angle pair for the diagnostic listing
                ASlp1 = ATN4(DG(1) - DG(0), HG(1) - HG(0)) / DEG2RAD  !344
                ASlp2 = ATN4(DG(M + 1) - DG(M), HG(M + 1) - HG(M)) / DEG2RAD  !345
                ! WARNING: SegLenFt is not initialized here, probably we should replicate lines 357-358
                ! Log terrain analysis for debugging if enabled
                if (DebugEnable == 1) then  !347
                    WRITE(3, FMT='("M=", I3, " DG(M)=", F10.3, " HG(M)=", F10.3, " DG(M+1)=", F10.3, " HG(M+1)=", F10.3)') &  !348
                        M, DG(M), HG(M), DG(M + 1), HG(M + 1)
                    WRITE(3, FMT='("M=", I3, " ASlp1=", F8.4, " ASlp2=", F8.4, " Len/Wave=", F8.3)') &  !349
                        M, ASlp1, ASlp2, SegLenFt / LAMBDA_FT
                end if
            end if
            ! For interior points, calculate the previous and next segment angles
            ! These are adjacent-segment angles, not centered finite differences
            if (M > 1 .and. NPointsSmoothed >= M + 1) then  !354
                ASlp1 = ATN4(DG(M) - DG(M-1), HG(M) - HG(M-1)) / DEG2RAD  !355
                ASlp2 = ATN4(DG(M+1) - DG(M), HG(M+1) - HG(M)) / DEG2RAD  !356
                SegLenFt = SQRT((HG(M+1) - HG(M)) * (HG(M+1) - HG(M)) &  !357
                               + (DG(M+1) - DG(M)) * (DG(M+1) - DG(M)))  !358
                ! Log detailed terrain slope analysis for each point
                if (DebugEnable == 1) then  !360
                    WRITE(3, FMT='("M=", I3, " DG(M)=", F10.3, " HG(M)=", F10.3, " DG(M+1)=", F10.3, " HG(M+1)=", F10.3)') &  !361
                        M, DG(M), HG(M), DG(M + 1), HG(M + 1)
                    WRITE(3, FMT='("M=", I3, " ASlp1=", F8.4, " ASlp2=", F8.4, " Len/Wave=", F8.3)') &  !364
                        M, ASlp1, ASlp2, SegLenFt / LAMBDA_FT
                end if
                ! ============================================================
                ! DIFFRACTION EDGE DETECTION CRITERIA
                ! ============================================================
                ! A terrain point qualifies as a diffraction-edge candidate if:
                ! 1. Degree-valued slope change exceeds DEG2RAD*0.5
                ! 2. Following segment length is greater than λ/100
                ! 3. The point is an interior terrain-profile point
                if (ABS(ASlp2 - ASlp1) > DEG2RAD * 0.5 &  !370
                    .and. SegLenFt > LAMBDA_FT * 0.01 .and. M > 1) then  !371
                    ! Additional guard uses OR, so any one condition is enough:
                    ! - point within 9999 ft, or following segment <= 20λ
                    ! - or either adjacent segment angle is nonzero
                    ! The guard accepts the point when any class matches
                    if (DG(M) < 9999.0 .or. SegLenFt / LAMBDA_FT <= 20.0 &  !376
                        .or. ASlp1 /= 0.0 .or. ASlp2 /= 0.0) then  !377
                        ! Mark this point as a selected diffraction edge
                        ! Add to the global diffraction point array for UTD processing
                        IsDiffPoint(M) = 1  !380
                        NDiffPoints = NDiffPoints + 1_I2  !381
                        DiffPtIdx(NDiffPoints) = INT(M, KIND=I2)  !384
                        if (DebugEnable == 1) then  !385
                            WRITE(3, FMT='(11X, "Select as diffraction point: ", I3)') M  !386
                        end if
                    end if
                    ! ================================================================
                    ! DIRECT RAY PATH ANALYSIS FOR EACH ANTENNA ELEMENT
                    ! ================================================================
                    ! For each diffraction point found, analyze line-of-sight conditions
                    ! from each antenna element to determine if direct propagation is possible
                    Loop_ElemScan: do ElemIdx = 1, NElements  !390
                        LaunchAngle = ATN4(DG(M), HG(M) - (HG(1) + HantFeetAbs(ElemIdx)))  !393
                        ! Calculate elevation angle from antenna element to diffraction point
                        RayHeightCurrent = HG(1) + HantFeetAbs(ElemIdx)  !395
                        do ScanIdx = 1, M  !396
                            ! Ray height prediction along straight-line path to check terrain clearance
                            HtRay = RayHeightCurrent + TAN(LaunchAngle) * (DG(ScanIdx) - DG(ScanIdx - 1))  !398
                            ! If ray goes below terrain, this path is blocked (no line-of-sight)
                            if (HtRay + 0.001 < HG(ScanIdx)) then  !400
                                ! Ray is obstructed by terrain - skip to next antenna element
                                ! No direct incident path to this edge is stored for this element
                                ! Other diffraction paths are considered through separate scans
                                CYCLE Loop_ElemScan  !405
                            end if
                            RayHeightCurrent = HtRay  !407
                        end do
                        ! Ray clears all terrain - compute path phase and store geometry
                        ! Phase calculation includes antenna element phase setting (0° or 180°)
                        if (AntPhase(ElemIdx-1) == -1) then  !412
                            PhaseToM = (DG(M) / COS(LaunchAngle)) * k + PI  !413
                        else if (AntPhase(ElemIdx-1) == 1) then  !414
                            PhaseToM = (DG(M) / COS(LaunchAngle)) * k  !415
                        end if
                        ! Store ray geometry for UTD calculations
                        ! Electrical path length in wavelengths for UTD distance parameter
                        AntEdgeDistWaves = ((DG(M) / COS(LaunchAngle)) / LAMBDA_FT)  !419
                        ! Store launch angle and phase for this antenna element and diffraction point
                        FAngle(ElemIdx, M) = LaunchAngle  !423
                        DiffPh0(ElemIdx, M) = PhaseToM  !424
                        ElemGain = COS(LaunchAngle * PATTERN_ELEV_NORM60_OVER_BW) * ARRAY_PATTERN_SCALE  !425
                        Slpe1 = ATN4(DG(M) - DG(M-1), HG(M) - HG(M-1))  !426
                        Slpe2 = ATN4(DG(M+1) - DG(M), HG(M+1) - HG(M))  !427
                        CALL ANGIN(Slpe1, Slpe2, LaunchAngle, Incl, &
                                   PhiP, PHR, NSteps)  !429
                        PHRStepNeg0p25 = -(DEG2RAD * 0.25)  !430
                        ! ============================================================
                        ! UTD ANGULAR SECTOR SCAN FOR DIFFRACTED FIELD CALCULATION
                        ! ============================================================
                        ! ANGIN has determined the angular sector and number of steps
                        ! Now scan through observation angles to calculate UTD diffraction coefficients
                        do SweepStepIdx = 1, NSteps  !431
                            PHR = PHRStepNeg0p25 + PHR  !432
                            UnusedUTDZero = 0.0  !433
                            ! Call YUTD for the scalar straight-wedge coefficient
                            ! This call uses one antenna-edge L_waves value for all four terms
                            CALL YUTD(FREQ_MHZ, AntEdgeDistWaves, PhiP, & !434
                                      Incl, PHR, &
                                      UTD_OutMag, UTD_OutPhase)
                            ! Check whether the UTD magnitude passes the cutoff
                            if (UTD_OutMag >= UTD_MAG_THRESHOLD) then  !439
                                OutputField = UTD_OutMag * ElemGain  !440
                                PhaseWork = PhaseToM - UTD_OutPhase  !443
                                CALL ANGHORIZ(Slpe1, PHR, PHRF)  !444
                                ! Trace the outgoing diffracted ray over the remaining terrain
                                HG_at_M = HG(M)  !449
                                ! Check if mapped outgoing angle is traceable by REFL
                                if (PHRF <= HALF_PI) then  !451
                                    ! Call REFL to trace the outgoing ray and apply Fresnel if it reflects
                                    M_i2 = INT(M, KIND=I2)  !453
                                    NPointsSmoothed_i2 = INT(NPointsSmoothed, KIND=I2)  !454
                                    CALL REFL(M_i2, NPointsSmoothed_i2, PHRF, HG_at_M, &  !455
                                              PhaseWork, ReflAmp, ReflPhase, HtRay, PHRout, &
                                              TotSlantFt, MadeItOut, MadeHit)
                                    OutputField = ReflAmp * OutputField  !458
                                    if (MadeItOut) then  !459
                                        ! ================================================
                                        ! COMPLEX FIELD ACCUMULATION IN ELEVATION PATTERN
                                        ! ================================================
                                        ! Convert angle to index; 4x oversampling ensures 0.25° resolution
                                        ! Maps elevation to array: idx = (angle_rad * 4) / (π/180)
                                        AngleIdx_f = (PHRout * 4.0) / DEG2RAD  !463
                                        ! Round to integer; handles discretization for pattern storage
                                        AngleIdx = NINT(AngleIdx_f)  !465
                                        ! Validate range; only 0°-35° contribute to final pattern (FOM uses 1°-35°)
                                        if (0.0 <= PHRout .and. PHRout <= DEG2RAD * 35.0) then  !467
                                            ! Track accepted diffraction contributions for count output
                                            TotalDiffCount = TotalDiffCount + 1_I2  !469
                                            ! Compute phase; includes reflection and height corrections
                                            FinalPhase = ReflPhase &  !471
                                                           - k * HtRay * &
                                                             SIN((AngleIdx * DEG2RAD) / 4.0) !473
                                            ! Coherent complex field accumulation: E = Σ A_i e^(jφ_i)
                                            ! Add this ray phasor into its exit-angle bin
                                            E_diffAccum(AngleIdx) = E_diffAccum(AngleIdx) &  !475
                                                                               + CMPLX(COS(FinalPhase), SIN(FinalPhase)) * OutputField  !476
                                            NCountDiff(AngleIdx) = NCountDiff(AngleIdx) + 1_I2  !477
                                            if (DebugEnable == 1) then  !480
                                                if (DebugMode == 0) then  !481
                                                    if (AngleIdx / 4.0 == DebugExitAngle) then  !482
                                                        WRITE(4, FMT='("At exit angle ", F8.3, " deg.  PHR = ", F8.3, " deg. at point: ", I3, /, "Launch Angle = ", F8.3)') &  !483
                                                              DebugExitAngle, &
                                                              PHR / DEG2RAD, &
                                                              M, &
                                                              FAngle(ElemIdx, M) / DEG2RAD

                                                        WRITE(4, FMT='("At M=", I3, 2X, "PhiP=", F7.3, 2X, "PHR=", F7.3, 2X, "Slpe1=", F7.3, 2X, "Slpe2=", F7.3, 2X, "Incl=", F7.3)') &  !489
                                                              M, PhiP / DEG2RAD, PHR / DEG2RAD, &
                                                              Slpe1 / DEG2RAD, Slpe2 / DEG2RAD, Incl / DEG2RAD

                                                        WRITE(4, FMT='("UTD OutMag = ", F8.3, "  UTD OutPhase = ", F8.3, " deg. => ", F8.3, " radians")') &  !494
                                                              UTD_OutMag, &
                                                              UTD_OutPhase / DEG2RAD, &
                                                              UTD_OutPhase

                                                        WRITE(4, FMT='("PHRF = ", F8.3, "  HtRay = ", F10.3, "  Slant dist. = ", F11.3, " lambda")') &  !499
                                                              PHRF / DEG2RAD, HtRay, AntEdgeDistWaves

                                                        WRITE(4, FMT='("Output Field = ", F8.3, "  Final Phase = ", F11.3, " radians.",/)') &  !502
                                                              OutputField, FinalPhase
                                                    end if
                                                else
                                                    ! Alternative debug output format for different debug modes
                                                    WRITE(4, FMT='("At exit angle ", F8.3, " deg.  PHR = ", F8.3, " deg. at point: ", I3, /, "Launch Angle = ", F8.3)') &  !507
                                                        DebugExitAngle, PHR / DEG2RAD, M, FAngle(ElemIdx, M) / DEG2RAD
                                                    WRITE(4, FMT='("At M=", I3, 2X, "PhiP=", F7.3, 2X, "PHR=", F7.3, 2X, "Slpe1=", F7.3, 2X, "Slpe2=", F7.3, 2X, "Incl=", F7.3)') &  !509
                                                        M, PhiP / DEG2RAD, PHR / DEG2RAD, Slpe1 / DEG2RAD, Slpe2 / DEG2RAD, Incl / DEG2RAD
                                                    WRITE(4, FMT='("UTD OutMag = ", F8.3, "  UTD OutPhase = ", F8.3, " deg. => ", F8.3, " radians")') &  !511
                                                        UTD_OutMag, UTD_OutPhase / DEG2RAD, UTD_OutPhase
                                                    WRITE(4, FMT='("PHRF = ", F8.3, "  HtRay = ", F10.3, "  Slant dist. = ", F11.3, " lambda")') &  !513
                                                        PHRF / DEG2RAD, HtRay, AntEdgeDistWaves
                                                    WRITE(4, FMT='("Output Field = ", F8.3, "  Final Phase = ", F11.3, " radians.",/)') &  !514
                                                        OutputField, UTD_OutPhase / DEG2RAD
                                                end if
                                            end if
                                        end if
                                    end if
                                end if
                            end if
                        end do
                    end do Loop_ElemScan
                end if
                ! ============================================================
                ! SINGLE-EDGE DIFFRACTION PROCESSING COMPLETE
                ! ============================================================
                ! Check if we've processed all terrain points or reached profile end
                ! Stop before the reduced profile no longer has a following segment
                if (NPointsSmoothed - 2 < M) then  !528
                    EXIT  !529
                end if
            end if
        end do

        ! ====================================================================
        ! MULTI-EDGE DIFFRACTION AND DIFFRACTION-REFLECTION-DIFFRACTION
        ! ====================================================================
        ! After single-edge UTD analysis, process multiple diffraction paths
        ! This handles cases where signals propagate via multiple terrain edges
        ! using one scalar coefficient and one L_waves proxy at each edge

        NDiffPoints_i4 = NDiffPoints  !539
        ! NDiffPoints_i4 now contains the total number of detected diffraction edges
        ! This count is used by DIFFDIFF and by the ProcessFlag-gated DRD branch

        if (DebugEnable == 1) then  !543
            WRITE(4, FMT='("Starting Diffraction to Diffraction Analysis.")')  !544
        end if
        ! DIFFDIFF: evaluates two-edge diffraction with cascaded UTD terms
        ! Two-edge paths: Antenna -> Edge1 -> Edge2 -> profile end
        CALL DIFFDIFF(NPointsSmoothed, NDiffPoints_i4, NElements, DebugEnable, DebugMode, &  !547
                      DebugExitAngle, AntPhase, E_diffAccum)
        ! DRD: diffraction-reflection-diffraction branch
        ! ProcessFlag gates this branch
        if (ProcessFlag == 0) then  !552
          CALL DRD(NPointsSmoothed, NDiffPoints_i4, NElements, DebugEnable, DebugMode, &  !553
                   DebugExitAngle, AntPhase, E_diffAccum)
        end if
    end if
    ! ========================================================================
    ! MAIN REFLECTION ANALYSIS - GEOMETRICAL OPTICS RAY TRACING
    ! ========================================================================
    ! This section implements the GO (Geometrical Optics) ray tracing for
    ! direct and reflected paths. Ray tracing scans elevation angles from -55° to +35°
    ! in 0.25° steps for finding reflection points, but pattern accumulation is gated to 0°-35°.
    !
    ! Theory: Geometrical-optics ray tracing with plane-wave Fresnel reflection
    ! coefficients for a lossy dielectric half-space.
    ! FRESNEL uses ABS of the outgoing ray angle in the horizontal coefficient form:
    ! Gamma_h(a)=(sin a - sqrt(eps_r-cos^2 a))/(sin a + sqrt(eps_r-cos^2 a))
    ! Complex eps_r uses soil relative permittivity and conductivity [S/m]

    LastPointIdx = NPointsSmoothed  !560

    if (DebugEnable == 1) then  !576
        WRITE(4, FMT='(/,"Starting Reflection and Refl./Diff. Analysis",/)')  !577
    end if
    ! Process each antenna element in the stacked array
    do ElemIdx = 1, NElements  !580
        RDHitIdx = 1  !581
        ! Initialize antenna element processing for current elevation scan
        ! Prepare ray tracing for each angle; covers -55° to +35° at 0.25° steps
        ! Sweep launch angles over terrain
        Loop_LaunchAngleScan: do LaunchIdxQ = -220, 140  !585
            AngleOutRad = (LaunchIdxQ * DEG2RAD) / 4.0  !591
            RayHeightCurrent = HG(1) + HantFeetAbs(ElemIdx)  !594
            ElemPatternAmp(ElemIdx, LaunchIdxQ) = COS(AngleOutRad * PATTERN_ELEV_NORM60_OVER_BW) * ARRAY_PATTERN_SCALE  !599
            if (AntPhase(ElemIdx - 1) == 1) then  !600
                ElemPhase(ElemIdx, LaunchIdxQ) = 0.0  !601
            else
                ElemPhase(ElemIdx, LaunchIdxQ) = PI  !603
            end if
            do M = 2, NPointsSmoothed  !605
                ! Process terrain segments to detect ray-ground interactions
                FoundRD = 0  !607
                ! Ray height at terrain segment end point - predict where ray intersects terrain
                RayHeightAtAngle(LaunchIdxQ) = TAN(AngleOutRad) * (DG(M) - DG(M-1)) + RayHeightCurrent  !609
                ! Check ray-terrain intersection: does ray clear terrain or hit ground?
                if (RayHeightAtAngle(LaunchIdxQ) > HG(M)) then  !611
                    ! ====================================================
                    ! RAY CLEARS TERRAIN - FREE-SPACE PROPAGATION SEGMENT
                    ! ====================================================
                    ! Ray passes above terrain with no reflection in this segment
                    ! Add segment electrical length to total phase accumulation
                    SlantSegFt(LaunchIdxQ) = (DG(M) - DG(M-1)) / COS(AngleOutRad)  !618
                    ElemPhase(ElemIdx, LaunchIdxQ) = ElemPhase(ElemIdx, LaunchIdxQ) &  !619
                                                               + k * SlantSegFt(LaunchIdxQ)  !620
                else
                    ! ====================================================
                    ! RAY HITS TERRAIN - COMPUTE REFLECTION POINT
                    ! ====================================================
                    ! Use analytical geometry to find exact intersection point
                    ! between ray and terrain segment (linear interpolation)
                    SegmentSlope = (HG(M) - HG(M-1)) / (DG(M) - DG(M-1))  !627
                    ! Solve ray-terrain intersection: ray_height = terrain_height
                    ReflectOffset = (RayHeightCurrent - HG(M-1)) / (SegmentSlope - TAN(AngleOutRad))  !629
                    ! Distance to reflection point from segment start
                    SlantSegFt(LaunchIdxQ) = ReflectOffset / COS(AngleOutRad)  !632
                    ElemPhase(ElemIdx, LaunchIdxQ) = ElemPhase(ElemIdx, LaunchIdxQ) &  !633
                                                               + k * SlantSegFt(LaunchIdxQ)  !634
                    ! Calculate reflection point coordinates
                    ReflectPointDistFt = ReflectOffset + DG(M-1)  !636
                    ! Height at reflection point
                    ReflectPointHeightFt = SegmentSlope * ReflectOffset + HG(M-1)  !638
                    SegmentAngleRad = ATN4(DG(M) - DG(M-1), HG(M) - HG(M-1))  !639
                    ! Apply the specular reflection law: theta_reflected = 2*terrain_angle - theta_incident
                    AngleOutRad = SegmentAngleRad * 2.0 - AngleOutRad  !641
                    if (AngleOutRad >= HALF_PI) then  !642
                        ! Reflected ray points past vertical
                        ! Set the limiting angle used by this branch
                        AngleOutRad = -(DEG2RAD * 90.0)  !645
                        EXIT
                    end if
                    ! Calculate path length from reflection point to terrain segment end
                    ! Compute reflected ray propagation distance and geometry
                    SlantSegFt(LaunchIdxQ) = (DG(M) - DG(M-1) - ReflectOffset) / COS(AngleOutRad)  !650
                    ! Update ray height after reflection using reflected angle
                    RayHeightAtAngle(LaunchIdxQ) = (SIN(AngleOutRad) * SlantSegFt(LaunchIdxQ) + ReflectPointHeightFt)  !652
                    PhaseWork = k * SlantSegFt(LaunchIdxQ) + ElemPhase(ElemIdx, LaunchIdxQ)  !653
                    ! Evaluate Fresnel at outgoing elevation; apply phase and save magnitude for RD
                    ElemPatternAmp_curr = ElemPatternAmp(ElemIdx, LaunchIdxQ)  !655
                    CALL FRESNEL(AngleOutRad, ElemPatternAmp_curr, PhaseWork, ReflGain, ReflPhase)  !656
                    ReflGainSaved = ReflGain  !657
                    ElemPhase(ElemIdx, LaunchIdxQ) = ReflPhase  !658
                    RayHeightPrev = RayHeightAtAngle(LaunchIdxQ)  !659
                    ! ========================================================
                    ! REFLECTION-DIFFRACTION INTERACTION DETECTION
                    ! ========================================================
                    ! Check whether the reflected ray passes close to a marked
                    ! downstream diffraction edge, creating an RD path
                    ! The detailed ray solve below confirms the candidate
                    if (RDHitIdx < M) then  !665
                        do Ipt = M + 1, NPointsSmoothed  !666
                            RayHeightPred = TAN(AngleOutRad) * (DG(Ipt) - DG(Ipt-1)) + RayHeightPrev  !667
                            ! Check vertical miss distance at a possible diffraction edge
                            if (ABS(RayHeightPred - HG(Ipt)) < 100.0) then  !669
                                ! If this point was marked as a diffraction edge earlier,
                                ! we have a reflection-diffraction path that
                                ! needs the UTD scan below
                                if (IsDiffPoint(Ipt) == 1) then  !674
                                    ! Mark interaction for reflection-diffraction processing
                                    FoundRD = 1  !676
                                    RDHitIdx = Ipt  !677
                                    EXIT
                                end if
                            end if
                            RayHeightPrev = RayHeightPred  !681
                        end do
                    end if
                    ! ========================================================
                    ! COMPLEX REFLECTION-DIFFRACTION PATH PROCESSING
                    ! ========================================================
                    if (FoundRD == 1) then  !686
                        ! Reset interaction flag and initialize iterative solver
                        FoundRD = 0  !688
                        ! Initialize convergence tracking for iterative ray solution
                        CoarseAdjustMode = 0  !690
                        AdjustSign = 1  !691
                        ! Reset the shooting solve for this RD candidate
                        ! Start again from the launch-grid angle
                        ! Track the height error at the marked diffraction point
                        IterCount = 0  !696
                        RayAngle0 = (LaunchIdxQ / 4.0) * DEG2RAD  !697
                        ! Use the current 0.25-degree launch angle as the first trial
                        ! Compare the traced height with the diffraction-point height
                        ! Recompute the path from the antenna toward that point
                        ! Prepare phase and path-length accumulators
                        LastHeightError = ABS(RayHeightPred - HG(Ipt))  !702
703                     RayAngle = RayAngle0  !703
                        RayHeight = HG(1) + HantFeetAbs(ElemIdx)  !704
                        ! Initialize path length and phase accumulators for ray integration
                        PhaseAccumRad = 0.0  !706
                        TotSlantFt = 0.0  !707
                        LastRayAngleBeforeRefl = 0.0  !708
                        ! Begin terrain segment traversal for current ray angle
                        do ScanIdx = 2, Ipt  !710
                            NextRayHeight = TAN(RayAngle) * (DG(ScanIdx) - DG(ScanIdx-1)) + RayHeight  !711
                            if (NextRayHeight > HG(ScanIdx)) then  !712
                                ! Ray travels above terrain - accumulate free-space path length
                                SlantSegLen = (DG(ScanIdx) - DG(ScanIdx-1)) / COS(RayAngle)  !714
                                TotSlantFt = SlantSegLen + TotSlantFt  !715
                                PhaseAccumRad = SlantSegLen * k + PhaseAccumRad  !716
                            else
                                ! Ray intersects terrain - calculate reflection geometry
                                SegSlope = (HG(ScanIdx) - HG(ScanIdx-1)) / (DG(ScanIdx) - DG(ScanIdx-1))  !719
                                AlongSegToIntersect = (RayHeight - HG(ScanIdx-1)) / (SegSlope - TAN(RayAngle))  !720
                                SlantSegLen = AlongSegToIntersect / COS(RayAngle)  !721
                                TotSlantFt = SlantSegLen + TotSlantFt  !722
                                PhaseAccumRad = SlantSegLen * k + PhaseAccumRad  !723
                                HeightAtIntersect = SegSlope * AlongSegToIntersect + HG(ScanIdx-1)  !724
                                SegAngle = ATN4(DG(ScanIdx) - DG(ScanIdx-1), HG(ScanIdx) - HG(ScanIdx-1))  !725
                                RayAngle = SegAngle * 2.0 - RayAngle  !726
                                if (ScanIdx <= Ipt - 1) then  !727
                                    ! Store final ray angle for subsequent calculations
                                    LastRayAngleBeforeRefl = RayAngle  !729
                                end if
                                if (RayAngle >= HALF_PI) then  !731
                                    RayAngle = -(DEG2RAD * 90.0)  !732
                                    CYCLE
                                else
                                    SlantSegLen = ((DG(ScanIdx) - DG(ScanIdx-1)) - AlongSegToIntersect) / COS(RayAngle)  !735
                                    TotSlantFt = SlantSegLen + TotSlantFt  !736
                                    PhaseAccumRad = SlantSegLen * k + PhaseAccumRad  !737
                                    PhaseWork = PhaseAccumRad  !738
                                    CALL FRESNEL(RayAngle, ReflGainSaved, PhaseWork, &  !739
                                                 ReflGain, ReflPhase)
                                    ElemPatternAmp(ElemIdx, LaunchIdxQ) = ReflGain  !741
                                    ! Update ray height using reflected angle and path length
                                    ! Apply specular reflection geometry at terrain intersection
                                    NextRayHeight = SIN(RayAngle) * SlantSegLen + HeightAtIntersect  !744
                                end if
                            end if
                            RayHeight = NextRayHeight  !746
                        end do
                        ! Check convergence - ray must reach the marked edge height
                        ! Evaluate difference between final ray height and that edge
                        ! Determine if additional iterations are needed for convergence
                        if (ABS(NextRayHeight - HG(Ipt)) > 0.1) then  !751
                            ! Height error exceeds tolerance - adjust ray angle iteratively
                            ! Compare current error with the stored starting error
                            if (LastHeightError < ABS(NextRayHeight - HG(Ipt))) then  !754
                                AdjustSign = -1  !755
                            end if
                            ! Apply angle correction for convergence to the marked edge height
                            if (CoarseAdjustMode == 0 .and. ABS(NextRayHeight - HG(Ipt)) > 10.0) then  !758
                                AngleAdjust = AdjustSign * 0.05 * DEG2RAD  !759
                                RayAngle0 = RayAngle0 - AngleAdjust  !760
                                ! Coarse adjustment phase - large angle steps for initial convergence
                                if (NextRayHeight > HG(Ipt)) then  !762
                                    UnusedWasAboveTerrain = .true.  !763
                                else
                                    UnusedWasAboveTerrain = .false.  !765
                                end if
                            else
                                AngleAdjust = AdjustSign * 0.001 * DEG2RAD  !768
                                RayAngle0 = RayAngle0 - AngleAdjust  !769
                            end if
                            ! Fine adjustment phase - small angle steps for precision convergence
                            if (ABS(NextRayHeight - HG(Ipt)) > 1000.0) then  !772
                                CYCLE  !773
                            end if
                            ! Increment iteration counter for convergence tracking
                            IterCount = IterCount + 1  !775
                            ! Check the local segment angle before retrying the solve
                            ! Negative or flat marked-edge geometry is rejected here
                            ! The next retry uses the adjusted launch angle
                            SlopeAtTarget = ATN4(DG(Ipt) - DG(Ipt-1), HG(Ipt) - HG(Ipt-1))  !779
                            if (SlopeAtTarget <= 0.0) then  !780
                                ! This RD search accepts only positive marked-edge segment angles
                                ! Nonpositive marked-edge segment angle; skip this ray path
                                ! Continue to next elevation angle
                                CYCLE  !784
                            end if
                            if (IterCount <= 10000) GOTO 703  !786
                            ! Maximum iterations exceeded - output debug information if enabled
                            if (DebugEnable == 1) then  !788
                                WRITE(4, FMT='(/,"Refl./Diff search, NTry = ", I4, "  H1 = ", F8.3, "  HG(", I3, ") = ", F8.3)') &  !789
                                      IterCount, NextRayHeight, Ipt, HG(Ipt)

                                WRITE(4, FMT='("Alpha1 = ", F8.3, "  Alpha2 = ", F8.3, "  TotDist = ", F8.3, " ft.")') &  !792
                                      RayAngle / DEG2RAD, LastRayAngleBeforeRefl / DEG2RAD, TotSlantFt
                            end if
                            ! Maximum iterations exceeded before convergence - skip this elevation
                            ! Ray tracing failed to converge to the marked edge height
                            CYCLE  !797
                        end if
                        ! RAY TRACING CONVERGED - Calculate final field contributions
                        ! Apply antenna element pattern factor for current elevation angle
                        ! Compute element gain and phase at the RD diffraction edge
                        ! Combine path length, Fresnel phase, and element phase
                        ! The following UTD scan diffracts from the marked edge
                        ElemGain = COS(RayAngle0 * PATTERN_ELEV_NORM60_OVER_BW) * ARRAY_PATTERN_SCALE  !805
                        ! Apply antenna element phase settings for coherent array summation
                        ! Calculate total phase including path length and reflection phase
                        if (AntPhase(ElemIdx - 1) == -1) then  !808
                          PhaseToRDEdgeRad = ((k * TotSlantFt + ReflPhase) - PhaseWork) + PI  !809
                        else
                          PhaseToRDEdgeRad = (k * TotSlantFt + ReflPhase) - PhaseWork  !811
                        end if
                        AngleOutRad = RayAngle0  !813
                        Slpe1 = ATN4(DG(Ipt) - DG(Ipt-1), HG(Ipt) - HG(Ipt-1))  !814
                        Slpe2 = ATN4(DG(Ipt+1) - DG(Ipt), HG(Ipt+1) - HG(Ipt))  !815
                        ! Calculate ANGIN angular parameters for diffraction
                        CALL ANGIN(Slpe1, Slpe2, LastRayAngleBeforeRefl, Incl, PhiP, &  !817
                                   PHR, NSteps)
                        if (DebugEnable == 1) then  !819
                            WRITE(4, FMT='("Refl. hit point #", I3, "  Launch=", F8.4, /)') &  !820
                                  Ipt, AngleOutRad / DEG2RAD
                        end if
                        ! Calculate direct slant distance for the direct-like path test
                        ! Compare ray-traced path with direct geometrical distance
                        DirectSlantToRDPoint = (DG(Ipt) / COS(FAngle(ElemIdx, Ipt)))  !825
                        ! Normalize traced path length for the YUTD distance parameter
                        ! Keep the direct-like path comparison in feet below
                        ! Evaluate if this represents a direct line-of-sight path
                        TotalSlantWaves = TotSlantFt / LAMBDA_FT  !829
                        ! Check if ray-traced path is approximately equal to direct path
                        ! Use a wavelength-based tolerance for the direct-like path test
                        ! Determine if this is actually a direct (non-reflected) ray
                        if (ABS(TotSlantFt - DirectSlantToRDPoint) < LAMBDA_FT * 0.1) then  !833
                            ! Ray path matches direct geometry - likely line-of-sight
                            ! Check elevation angle against terrain clearance angle
                            if (ABS(RayAngle0) - ABS(FAngle(ElemIdx, Ipt)) < 0.0044) then  !836
                                ! This is a direct-like shot, not an RD contribution
                                if (DebugEnable == 1) then  !838
                                    WRITE(4, FMT='("Going to 500 -- was direct shot", /)')  !839
                                end if
                                ! Skip this launch after identifying the direct-like shot
                                CYCLE  !842
                            end if
                        end if
                        PHRStepNeg0p25 = -(DEG2RAD * 0.25)  !845
                        do SweepStepIdx = 1, NSteps  !846
                            PHR = PHRStepNeg0p25 + PHR  !847
                            UnusedUTDZero = 0.0  !848
                            CALL YUTD(FREQ_MHZ, TotalSlantWaves, PhiP, Incl, PHR, &  !849
                                      UTD_OutMag, UTD_OutPhase)
                            if (UTD_OutMag >= UTD_MAG_THRESHOLD) then  !851
                                OutputField = UTD_OutMag * ElemGain  !852
                                PhaseAccumRad = PhaseToRDEdgeRad - UTD_OutPhase  !854
                                CALL ANGHORIZ(Slpe1, PHR, PHRF)  !855
                                RayHeightCurrent = HG(Ipt)  !856
                                ! Map the local UTD scan angle to a traceable outgoing ray
                                ! Reject directions outside the REFL angular range
                                if (PHRF <= HALF_PI) then  !859
                                    RDPoint_i2 = INT(Ipt, KIND=I2)  !861
                                    NSmoothedPts_i2 = INT(NPointsSmoothed, KIND=I2)  !862
                                    CALL REFL(RDPoint_i2, NSmoothedPts_i2, PHRF, RayHeightCurrent, PhaseAccumRad, ReflAmp, &  !863
                                              ReflPhase, HtRayOut, AngleOutRad_RD, TotSlantFt, MadeItOut, MadeHit)
                                    PHRF = AngleOutRad_RD  !865
                                    OutputField = ReflAmp * OutputField  !866
                                    HtRay = HtRayOut  !867
                                    AngleIdx_f = (AngleOutRad_RD * 4.0) / DEG2RAD  !868
                                    AngleIdx = NINT(AngleIdx_f)  !869
                                    if ((0.0 <= PHRF) .and. (PHRF <= DEG2RAD * 35.0)) then  !870
                                        TotalDiffCount = TotalDiffCount + 1_I2  !871
                                        ! Use REFL's returned angle and height for this RD output bin
                                        FinalPhase = ReflPhase - SIN((AngleIdx * DEG2RAD) / 4.0) * k * HtRay  !873
                                        ! Add the angle-accepted RD phasor into the diffraction accumulator
                                        ! Apply the returned height in the phase correction
                                        E_diffAccum(AngleIdx) = E_diffAccum(AngleIdx) &  !876
                                                                           + CMPLX(COS(FinalPhase), SIN(FinalPhase)) * OutputField  !877
                                        NCountDiff(AngleIdx) = NCountDiff(AngleIdx) + 1_I2  !878
                                        ! Generate detailed debug output for specified angles if enabled
                                        ! Track accepted diffraction contributions for count output
                                        if (DebugEnable == 1) then  !881
                                            if (DebugMode == 0) then  !882
                                                if (AngleIdx / 4.0 == DebugExitAngle) then  !883
                                                    WRITE(4, FMT='("At exit angle ", F8.3, " deg.  PHR = ", F8.3, " deg. at point: ", I3, /, "Launch Angle = ", F8.3)') &  !884
                                                        DebugExitAngle, PHR / DEG2RAD, Ipt, &
                                                        RayAngle0 / DEG2RAD
                                                    WRITE(4, FMT='("At M=", I3, 2X, "PhiP=", F7.3, 2X, "PHR=", F7.3, 2X, "Slpe1=", F7.3, 2X, "Slpe2=", F7.3, 2X, "Incl=", F7.3)') &  !886
                                                        Ipt, PhiP / DEG2RAD, PHR / DEG2RAD, &
                                                        Slpe1 / DEG2RAD, Slpe2 / DEG2RAD, Incl / DEG2RAD
                                                    WRITE(4, FMT='("UTD OutMag = ", F8.3, "  UTD OutPhase = ", F8.3, " deg. => ", F8.3, " radians")') &  !888
                                                        UTD_OutMag, UTD_OutPhase / DEG2RAD, UTD_OutPhase
                                                    WRITE(4, FMT='("PHRF = ", F8.3, "  HtRay = ", F10.3, "  Slant dist. = ", F11.3, " lambda")') &  !890
                                                        PHRF / DEG2RAD, HtRay, TotalSlantWaves
                                                    WRITE(4, FMT='("Output Field = ", F8.3, "  Final Phase = ", F11.3, " radians.",/)') &  !891
                                                        OutputField, FinalPhase
                                                end if
                                            else
                                                WRITE(4, FMT='("At exit angle ", F8.3, " deg.  PHR = ", F8.3, " deg. at point: ", I3, /, "Launch Angle = ", F8.3)') &  !894
                                                    REAL(AngleIdx) / 4.0, PHR / DEG2RAD, Ipt, &
                                                    RayAngle0 / DEG2RAD
                                                WRITE(4, FMT='("At M=", I3, 2X, "PhiP=", F7.3, 2X, "PHR=", F7.3, 2X, "Slpe1=", F7.3, 2X, "Slpe2=", F7.3, 2X, "Incl=", F7.3)') &  !896
                                                    M, PhiP / DEG2RAD, PHR / DEG2RAD, &
                                                    Slpe1 / DEG2RAD, Slpe2 / DEG2RAD, Incl / DEG2RAD
                                                WRITE(4, FMT='("UTD OutMag = ", F8.3, "  UTD OutPhase = ", F8.3, " deg. => ", F8.3, " radians")') &  !898
                                                    UTD_OutMag, UTD_OutPhase / DEG2RAD, UTD_OutPhase
                                                WRITE(4, FMT='("PHRF = ", F8.3, "  HtRay = ", F10.3, "  Slant dist. = ", F11.3, " lambda")') &  !900
                                                    PHRF / DEG2RAD, HtRay, TotalSlantWaves
                                                WRITE(4, FMT='("Output Field = ", F8.3, "  Final Phase = ", F11.3, " radians.",/)') &  !901
                                                    OutputField, FinalPhase
                                            end if
                                        end if
                                    end if
                                end if
                            end if
                        end do
                        ! RD processing is complete for this launch
                        ! Suppress the GO contribution for the launch that entered this branch
                        ! Continue with the next launch angle
                        ! Any accepted RD phasors were already accumulated above
                        ElemPatternAmp(ElemIdx, LaunchIdxQ) = 0.0  !913
                        CYCLE Loop_LaunchAngleScan  !914
                    end if
                end if
                ! Carry the traced ray height forward to the next terrain point
                ! If no RD branch was entered, the GO contribution is handled below
                ! The current launch angle remains the GO output angle
                ! Terrain clearance has been tested segment by segment
                RayHeightCurrent = RayHeightAtAngle(LaunchIdxQ)  !921
            end do
            ! GO RAY PROCESSING - direct or already-reflected ray contribution
            ! Convert final elevation angle to pattern array index
            ! Maps to 0.25° bins: idx = (angle_rad * 4) / (π/180)
            ! Round to nearest 0.25° for array; handles discretization
            ! Store angle index for this antenna element and elevation
            ! Apply phase corrections for the geometrical-optics ray path
            AngleIdx_f = (AngleOutRad * 4.0) / DEG2RAD  !928
            ! Round to nearest 0.25° increment for array indexing
            AngleIdx = NINT(AngleIdx_f)  !930
            AngleIdxByElemLaunch(ElemIdx, LaunchIdxQ) = INT(AngleIdx, KIND=I2)  !931
            ! Apply the final height-dependent phase correction
            ! RayHeightAtAngle contains the last traced height for this launch
            ! The angle bin selects the sine term in the phase correction
            ! ElemPhase already contains path phase, element phase, and Fresnel phase
            ! Accumulate the GO phasor in the output angle bin
            ! Multiple enabled elements add coherently in the same bin
            ! ElemPatternAmp contains the element pattern amplitude for this GO launch
            ! The final phase is held in radians for the complex sum
            ! This is the last phase update before GO accumulation
            ! Calculate final phase including path and height corrections
            ElemPhase(ElemIdx, LaunchIdxQ) = ElemPhase(ElemIdx, LaunchIdxQ) &  !942
                                                       - SIN((AngleIdx * DEG2RAD) / 4.0) * k * RayHeightAtAngle(LaunchIdxQ)  !943
            ! Store final phase for the GO ray contribution
            FinalPhaseGO = ElemPhase(ElemIdx, LaunchIdxQ)  !945
            ! Add GO ray field to elevation pattern array if within valid range
            if ((0 <= AngleIdx) .and. (AngleIdx <= 181)) then  !947
                E_goAccum(AngleIdx) = E_goAccum(AngleIdx) &  !948
                                                   + CMPLX(COS(FinalPhaseGO), SIN(FinalPhaseGO)) &
                                                     * ElemPatternAmp(ElemIdx, LaunchIdxQ)
                if (DebugEnable == 1) then  !951
                    if (DebugMode == 0) then  !952
                        if (AngleIdx / 4.0 == DebugExitAngle) then  !953
                            WRITE(4, FMT='("Refl: Launch  = ", F7.3, " deg.  Angle out = ", F7.3, " deg.", /, &
                                           & "Ampl. = ", F7.3, "  Phase = ", F11.3, " radians", /)') &
                                REAL(LaunchIdxQ) / 4.0, &
                                AngleOutRad / DEG2RAD, &
                                SQRT( (COS(FinalPhaseGO) * ElemPatternAmp(ElemIdx, LaunchIdxQ))**2 + &
                                      (SIN(FinalPhaseGO) * ElemPatternAmp(ElemIdx, LaunchIdxQ))**2 ), &
                                FinalPhaseGO
                        end if
                    else
                        WRITE(4, FMT='("Refl: Launch  = ", F7.3, " deg.  Angle out = ", F7.3, " deg.", /, &
                                       & "Ampl. = ", F7.3, "  Phase = ", F11.3, " radians", /)') &
                            REAL(LaunchIdxQ) / 4.0, &
                            AngleOutRad / DEG2RAD, &
                            SQRT( (COS(FinalPhaseGO) * ElemPatternAmp(ElemIdx, LaunchIdxQ))**2 + &
                                  (SIN(FinalPhaseGO) * ElemPatternAmp(ElemIdx, LaunchIdxQ))**2 ), &
                            FinalPhaseGO
                    end if
                end if
            end if
        end do Loop_LaunchAngleScan
    end do

    if (DebugEnable == 1) then  !974
        WRITE(4, FMT='("Total diffraction components = ", I5, //)') TotalDiffCount  !975
        ! DEBUG OUTPUT SECTION - terrain profile used by the ray trace
        ! Print distance and height coordinates after profile thinning
        ! The first point is printed explicitly, then populated points
        ! This listing matches the working DG/HG arrays used above
        ! Points with zero distance are omitted in the loop below
        ! The far sentinel point is included when present in DG/HG
        ! These values are enough to check a plotted terrain profile
        ! No field calculation is changed by this diagnostic block
        WRITE(4, FMT='("DG(", I3, ") = ", F8.1, "   HG(", I3, ") = ", F8.1)') &
            1, DG(1), 1, HG(1)
        do Ipt = 2, 150  !986
            if (DG(Ipt) > 0.0) then  !987
                WRITE(4, FMT='("DG(", I3, ") = ", F8.1, "   HG(", I3, ") = ", F8.1)') &  !988
                    Ipt, DG(Ipt), Ipt, HG(Ipt)
            end if
        end do
    end if
    ! ========================================================================
    ! FIELD COMBINATION AND PATTERN SYNTHESIS
    ! ========================================================================
    ! Coherently combine GO and diffracted ray contributions
    ! Apply antenna array factors and element patterns
    ! Integrate diffraction and geometrical optics contributions
    ! Sum complex field amplitudes across all propagation paths
    ! Account for multiple antenna elements in phased array
    ! Keep phase until the GO and diffraction accumulators are combined
    ! Prepare final pattern magnitudes for smoothing and output formatting
    ! ========================================================================
    ! FINAL PATTERN SYNTHESIS AND OUTPUT GENERATION
    ! ========================================================================
    ! Combine all propagation mechanisms represented by the accumulators
    ! Apply moving-average smoothing and convert to dB for final output

    ! Coherent summation of all field contributions: GO + diffraction
    do AngleIdx_0_180 = 0, 180  !1006
        ! Vector addition of complex fields from all propagation paths:
        ! Total_field = GO_field + Diffraction_field
        E_total_tmp(AngleIdx_0_180) = E_goAccum(AngleIdx_0_180) + E_diffAccum(AngleIdx_0_180)  !1009
    end do
    ! Convert complex field to magnitude with numerical stability threshold
    do AngleIdx_1_180 = 1, 180  !1012
        ! Avoid numerical issues with zero fields by setting minimum threshold
        if (ABS(E_total_tmp(AngleIdx_1_180)) <= 0.0001) then  !1014
            E_total_tmp(AngleIdx_1_180) = CMPLX(0.0001, 0.0001)  !1015
        end if
        ! Extract field magnitude for pattern calculation
        ! This gives the antenna pattern before dB conversion and smoothing
        PatternMag(AngleIdx_1_180) = ABS(E_total_tmp(AngleIdx_1_180))  !1020
    end do
    ! Close debug files if they were opened
    if (DebugEnable == 1) then  !1024
        CLOSE(UNIT=3, STATUS='KEEP')  !1025
        CLOSE(UNIT=4, STATUS='KEEP')  !1026
        CLOSE(UNIT=5, STATUS='KEEP')  !1027
    end if
    ! ========================================================================
    ! 5-POINT SMOOTHING FILTER AND dB CONVERSION
    ! ========================================================================
    ! Apply 5-point averaging to scalar magnitudes before dB conversion.
    ! Phase has already been discarded in PatternMag.
    do SmoothIdx = 1, 140
        ! Apply 5-point smoothing for points with sufficient neighbors
        if (SmoothIdx > 2) then  !1034
            Pattern_dB(SmoothIdx-1) = 20.0 * LOG10(SUM(PatternMag(SmoothIdx-2:SmoothIdx+2)) / 5.0)  !1035
        else if (SmoothIdx == 2) then
            Pattern_dB(SmoothIdx-1) = 20.0 * LOG10(SUM(PatternMag(1:3)) / 3.0)  !1038
        else
            ! First output bin is set to the displayed low-end floor
            Pattern_dB(SmoothIdx-1) = -30.0  !1041
        end if
    end do
    ! Set pattern floor at the first two bins (near horizon)
    ! Indices 0 and 1 correspond to 0.25° and 0.50°; force to -30 dB
    Pattern_dB(0) = -30.0  !1048
    Pattern_dB(1) = -30.0  !1049

    ! 1052..1055: redundant file closing!

end subroutine  !1061


! ================================================================================
! REFL: Ray Tracing with Fresnel Reflection Coefficients
! ================================================================================
! Purpose: Traces a ray from IptStart to IptEnd over terrain profile.
!          Terrain hits update phase through FRESNEL; ReflAmp is segment-local.
!
! Theory: Implements geometrical-optics ray tracing with Fresnel reflection:
!         Gamma_h(a)=(sin a-sqrt(eps_r-cos^2 a))/(sin a+sqrt(eps_r-cos^2 a))
!         where a is the FRESNEL angle argument and eps_r = eps' - j*sigma/(omega*eps0)
!
! Input Parameters:
!   IptStart       - Starting terrain point index
!   IptEnd         - Ending terrain point index
!   RayAngle0      - Initial ray elevation angle [radians]
!   RayHeight0     - Initial ray height [feet]
!
! Output/Input Parameters:
!   FinalPhase     - Input phase accumulator [radians]
!   ReflAmp        - 1.0 after a clear segment; Fresnel magnitude if last segment reflected
!   PhaseAfterRefl - Final phase including any reflection phase [radians]
!   RayHeight      - Final ray height [feet]
!   RayAngle       - Final ray elevation angle [radians]
!   TotSlantFt     - Accumulated path-distance quantity returned to caller [feet]
!   MadeItOut      - Ray made it out flag (beyond terrain profile)
!   MadeHit        - Ray reached endpoint height without clearing above it
!
! Algorithm: Segment-by-segment ray tracing with specular reflection analysis
! ================================================================================
subroutine REFL( IptStart, IptEnd, RayAngle0, RayHeight0, FinalPhase, ReflAmp, PhaseAfterRefl, RayHeight, RayAngle, TotSlantFt, MadeItOut, MadeHit )  !1063
    implicit none
    integer*2 IptStart, IptEnd
    logical MadeItOut, MadeHit
    real*4 RayAngle0, RayHeight0, FinalPhase, ReflAmp, PhaseAfterRefl, RayHeight, RayAngle, TotSlantFt

    integer*4 Ipt
    real*4 FresnelAngle, PhaseIn, SegmentAngleRad, ReflectPointHeightFt, ReflectPointDistFt, AlongSegToIntersect, SegSlope, SlantSegLen, RayHeightCurr

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    real*4 DG(0:150), HG(0:150), FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE
    common /Params/ DG, HG, FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE

    real*4, external :: ATN4

    ! Initialize output parameters before tracing the requested segment range
    ! Defaults represent no completed path until the loop proves otherwise

    MadeItOut = .false.  !1095
    MadeHit = .false.  !1096
    RayHeight = 0.0  !1097
    !FLOAT_10018788 = FinalPhase  !1098
    RayAngle = RayAngle0  !1099
    PhaseAfterRefl = FinalPhase  !1100
    RayHeightCurr = RayHeight0  !1101
    TotSlantFt = 0.0  !1102
    do Ipt = IptStart+1, IptEnd  !1103
        RayHeight = (TAN(RayAngle) * (DG(Ipt) - DG(Ipt-1)) + RayHeightCurr)  !1104
        if (RayHeight + 0.001 > HG(Ipt)) then  !1105
            ! Ray clears terrain - add path length and set this segment amplitude to 1
            SlantSegLen = ((DG(Ipt) - DG(Ipt-1)) / COS(RayAngle))  !1107
            TotSlantFt = SlantSegLen + TotSlantFt  !1108
            PhaseAfterRefl = SlantSegLen * k + PhaseAfterRefl  !1109
            ReflAmp = 1.0  !1110
        else
            ! Ray intersects terrain - calculate reflection point geometry
            if (DG(Ipt) - DG(Ipt-1) == 0.0) then  !1113
                SegSlope = 0.0  !1114
            else
                SegSlope = (HG(Ipt) - HG(Ipt-1)) / (DG(Ipt) - DG(Ipt-1))  !1116
            end if
            AlongSegToIntersect = ((RayHeightCurr - HG(Ipt-1)) / (SegSlope - TAN(RayAngle)))  !1118
            SlantSegLen = (AlongSegToIntersect / COS(RayAngle))  !1119
            PhaseAfterRefl = SlantSegLen*k + PhaseAfterRefl  !1120
            ReflectPointDistFt = AlongSegToIntersect + DG(Ipt-1)  !1121
            TotSlantFt = ReflectPointDistFt + TotSlantFt  !1122
            ReflectPointHeightFt = SegSlope * AlongSegToIntersect + HG(Ipt-1)  !1123
            SegmentAngleRad = ATN4(DG(Ipt) - DG(Ipt-1), HG(Ipt) - HG(Ipt-1))  !1124
            RayAngle = SegmentAngleRad * 2.0 - RayAngle  !1126
            if (ABS(RayAngle) >= HALF_PI) then  !1127
                RayAngle = -HALF_PI  !1128
                MadeItOut = .false.  !1129
                exit  !1130
            end if
            SlantSegLen = ((DG(Ipt) - DG(Ipt-1) - AlongSegToIntersect) / COS(RayAngle))  !1132
            RayHeight = (SIN(RayAngle) * SlantSegLen + ReflectPointHeightFt)  !1133
            TotSlantFt = SlantSegLen + TotSlantFt  !1134
            PhaseAfterRefl = SlantSegLen * k + PhaseAfterRefl  !1135
            PhaseIn = PhaseAfterRefl  !1137
            FresnelAngle = RayAngle  !1138
            CALL FRESNEL(FresnelAngle, 1.0, PhaseIn, ReflAmp, PhaseAfterRefl)  !1139
        end if
        if (IptEnd == Ipt .AND. HG(IptEnd) + 0.01 < RayHeight) then  !1141
            MadeItOut = .true.  !1142
        end if
        if (IptEnd == Ipt .and. ABS(RayHeight - HG(IptEnd)) < 0.01 & !1144
                                   .and. (.not. MadeItOut)) then  !1145
            MadeHit = .true.  !1146
        end if
        RayHeightCurr = RayHeight  !1148

    end do

end subroutine  !1152
