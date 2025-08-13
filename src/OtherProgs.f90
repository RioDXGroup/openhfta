! ================================================================================
! DIFFDIFF: Two-Edge Diffraction Analysis Using Cascaded Scalar UTD Terms
! ================================================================================
! Purpose: Computes paths that diffract at two terrain edges in sequence,
!          cascading the same scalar UTD coefficient used elsewhere
!
! Theory: Uses the scalar straight-wedge coefficient at both terrain edges:
!         Total field contribution = D1(edge1) * D2(edge2) * path factors
!         Each YUTD call receives one path-length proxy for L_waves
!
! Algorithm: For each antenna element and edge pair:
! 1. Check whether Antenna->Edge1->Edge2 has stored/traceable geometry
! 2. Apply UTD at first edge with incident field from antenna
! 3. Propagate diffracted field to second edge
! 4. Apply UTD at second edge with field from first edge
! 5. Sum coherently into elevation pattern array
!
! Input Parameters:
!   NPoints        - Number of terrain points
!   NDiffPoints    - Number of diffraction edges found
!   NElements      - Number of antenna elements
!   DebugEnable    - Debug output enable flag
!   DebugMode      - Debug mode selector
!   DebugExitAngle - Debug elevation angle for detailed output
!   AntPhase       - Antenna phase array (unused dummy in this routine)
!
! Output Parameters:
!   E_diffAccum    - Complex elevation pattern array (accumulated diffraction contributions)
!
! ================================================================================
subroutine DIFFDIFF ( NPoints, NDiffPoints, NElements, DebugEnable, DebugMode, DebugExitAngle, AntPhase, E_diffAccum )  !3
    implicit none
    integer*4 NPoints, NDiffPoints, NElements, DebugEnable, DebugMode
    real*4 DebugExitAngle
    integer*2 AntPhase(*)
    complex*8 E_diffAccum(0:181)

    real*4 FinalPhase2, AngleIdx_f2, OutputField2, UnusedTotSlant2, AngleOut2
    real*4 ReflPhase2, HG_at_E2, PHRF2, AmpAtE2, PhaseAtE2
    real*4 L12_waves, PHRStepNeg0p25, Slpe2_edge2, Slpe1_edge2
    real*4 PhaseAfterE1, AmpAfterE1, UTD_OutPhase, UTD_OutMag, L1_waves
    real*4 E1PhaseLengthFt, PHR, PhiP, AInclA, Slpe2_edge1
    real*4 Slpe1_edge1, ElemGain, SlantDist12_ft, UnusedAngleOut1, UnusedReflPhase1
    real*4 ReflAmpTrace, ReflPhaseSeed, RayHeightOut2, Edge12Angle
    logical MadeHit, MadeItOut
    integer*4 AngleIdx2, StepIdx2, NSteps1, EdgeIdx2, EdgeIdx1, ElemIdx
    integer*2 NPoints_i2, E2_i2, Edge2_i2, Edge1_i2

    integer*2 DiffPtIdx(1:200), EdgePairUsed(1:200, 1:200), NCountDiff(0:180), TotalDiffCount
    real*4 DiffPh0(1:4, 1:200), FAngle(1:4, 1:200)
    common /Globals/ DiffPtIdx, EdgePairUsed, NCountDiff, TotalDiffCount, DiffPh0, FAngle

    real*4 DG(0:150), HG(0:150), FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE
    common /Params/ DG, HG, FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    real*4, external :: ATN4

    integer, parameter :: I2 = selected_int_kind(4)

    if (.false.) AntPhase(1) = 0  ! suppress unused dummy argument warning

    do ElemIdx = 1, NElements  !37
        do EdgeIdx1 = 1, NDiffPoints  !38
            ! ================================================================
            ! FIRST EDGE PROCESSING FOR TWO-EDGE DIFFRACTION
            ! ================================================================
            ! Loop through ordered pairs of diffraction edges
            ! Accepted pairs get one coefficient at each edge
            do EdgeIdx2 = EdgeIdx1 + 1, NDiffPoints  !44
                if (DiffPtIdx(EdgeIdx2) - DiffPtIdx(EdgeIdx1) == 1) then  !45
                    ! Skip adjacent terrain points; no intervening segment is traced
                    CYCLE  !47
                end if
                if (NDiffPoints >= EdgeIdx2) then  !49
                    ! Calculate the ray angle from the first edge to the second
                    Edge12Angle = ATN4(DG(DiffPtIdx(EdgeIdx2)) - DG(DiffPtIdx(EdgeIdx1)), HG(DiffPtIdx(EdgeIdx2)) -  HG(DiffPtIdx(EdgeIdx1)))  !52
                else
                    ! Fallback branch for a missing downstream edge
                    RayHeightOut2 = 0.0  !55
                    CYCLE  !56
                end if
                ! ============================================================
                ! UTD PATH SETUP AND FIRST EDGE CALCULATION
                ! ============================================================
                ! Check whether this element stored a direct path to edge 1
                ! (This was computed in main YTWCore1 during edge detection)
                if (DiffPh0(ElemIdx, DiffPtIdx(EdgeIdx1)) > 0.0) then  !63
                    ! Initialize phase accumulator for the edge-to-edge REFL trace
                    ReflPhaseSeed = 0.0  !65
                    Edge1_i2 = DiffPtIdx(EdgeIdx1)  !66
                    Edge2_i2 = DiffPtIdx(EdgeIdx2)  !67
                    CALL REFL(Edge1_i2, Edge2_i2, Edge12Angle, &
                              HG(DiffPtIdx(EdgeIdx1)), ReflPhaseSeed, &
                              ReflAmpTrace, UnusedReflPhase1, RayHeightOut2, &
                              UnusedAngleOut1, SlantDist12_ft, MadeItOut, &
                              MadeHit)  !68
                    ! Check if the REFL trace reaches the second edge
                    ! Validate inter-edge path feasibility and continuation
                    if (MadeHit) then  !75
                        ! Mark edge pair as used for diffraction path
                        ! Set interaction flag for first and second edges
                        ! Record successful diffraction path between edge points
                        EdgePairUsed(DiffPtIdx(EdgeIdx1), DiffPtIdx(EdgeIdx2)) = 1  !79
                        ! Apply antenna element pattern factor for diffraction path
                        ! Calculate amplitude correction for current antenna orientation
                        ElemGain = COS(PATTERN_ELEV_NORM60_OVER_BW * FAngle(ElemIdx, DiffPtIdx(EdgeIdx1))) * ARRAY_PATTERN_SCALE  !82
                        ! Compute adjacent terrain angles at the first edge
                        ! Derive local wedge/incidence parameters for YUTD
                        ! Extract segment angles before/after the terrain vertex
                        ! Prepare the angular scan used by the diffraction coefficient
                        ! Keep this geometry local to the current edge pair
                        Slpe1_edge1 = ATN4(DG(DiffPtIdx(EdgeIdx1)  ) - DG(DiffPtIdx(EdgeIdx1)-1), &  !88
                                              HG(DiffPtIdx(EdgeIdx1)  ) - HG(DiffPtIdx(EdgeIdx1)-1))  !89
                        Slpe2_edge1 = ATN4(DG(DiffPtIdx(EdgeIdx1)+1) - DG(DiffPtIdx(EdgeIdx1)), &  !90
                                              HG(DiffPtIdx(EdgeIdx1)+1) - HG(DiffPtIdx(EdgeIdx1)))
                        CALL ANGIN(Slpe1_edge1, Slpe2_edge1, &  !92
                                   FAngle(ElemIdx, DiffPtIdx(EdgeIdx1)), &
                                   AInclA, PhiP, PHR, NSteps1)
                        if (Slpe1_edge1 < 0.0) then  !95
                            PHR = PI - Edge12Angle - ABS(Slpe1_edge1)  !96
                        else
                            PHR = ABS(Slpe1_edge1) + PI - Edge12Angle  !98
                        end if
                        ! Apply diffraction coefficient for first edge
                        ! Convert stored phase to an equivalent path length
                        ! The stored phase may include the element's 180-degree setting
                        ! This is the L_waves proxy for the first-edge coefficient
                        ! Keep PhiP/AInclA as the angular pair for this edge geometry
                        E1PhaseLengthFt = DiffPh0(ElemIdx, DiffPtIdx(EdgeIdx1)) / k  !105
                        ! Normalize path length by wavelength for UTD calculation
                        L1_waves = E1PhaseLengthFt / LAMBDA_FT  !107
                        ! Apply first UTD coefficient for edge diffraction
                        CALL YUTD(FREQ_MHZ, L1_waves, PhiP, AInclA, &  !109
                                  PHR, UTD_OutMag, UTD_OutPhase)
                        ! Use the first-edge coefficient without an intermediate cutoff
                        AmpAfterE1 = UTD_OutMag * ElemGain  !112
                        ! Calculate total phase from antenna to first edge including UTD phase
                        ! Prepare phase accumulation for second edge diffraction
                        PhaseAfterE1 = DiffPh0(ElemIdx, DiffPtIdx(EdgeIdx1)) - UTD_OutPhase  !115
                        ! Calculate terrain slope angles at second diffraction edge
                        Slpe1_edge2 = ATN4(DG(DiffPtIdx(EdgeIdx2  ))-DG(DiffPtIdx(EdgeIdx2)-1), &  !117
                                              HG(DiffPtIdx(EdgeIdx2  ))-HG(DiffPtIdx(EdgeIdx2)-1))  !118
                        Slpe2_edge2 = ATN4(DG(DiffPtIdx(EdgeIdx2)+1)-DG(DiffPtIdx(EdgeIdx2)  ), &  !119
                                              HG(DiffPtIdx(EdgeIdx2)+1)-HG(DiffPtIdx(EdgeIdx2)  ))
                        ! Calculate Incl/PhiP angular parameters for edge 2
                        CALL ANGIN(Slpe1_edge2, Slpe2_edge2, Edge12Angle, &
                                   AInclA, PhiP, PHR, &
                                   NSteps1)  !124
                        PHRStepNeg0p25 = -(DEG2RAD * 0.25)  !125
                        do StepIdx2 = 1, NSteps1  !126
                            PHR = PHRStepNeg0p25 + PHR  !127
                            !FLOAT_10011e2c = 0.0  !128
                            ! Apply second UTD coefficient for edge-to-edge diffraction
                            ! Calculate path length from first edge to second edge
                            ! Normalize by wavelength for diffraction calculation
                            L12_waves = SlantDist12_ft / LAMBDA_FT  !132
                            CALL YUTD(FREQ_MHZ, L12_waves, PhiP, &  !133
                                      AInclA, PHR, UTD_OutMag, &
                                      UTD_OutPhase)
                            ! Combine UTD coefficients from both diffraction edges
                            PhaseAtE2 = k * SlantDist12_ft + PhaseAfterE1 - UTD_OutPhase  !137
                            if (UTD_OutMag >= UTD_MAG_THRESHOLD) then  !138
                                AmpAtE2 = UTD_OutMag * AmpAfterE1  !139
                                CALL ANGHORIZ(Slpe1_edge2, PHR, PHRF2)  !140
                                ! Trace the outgoing path from the second edge
                                ! Set height at second diffraction edge for final ray tracing
                                HG_at_E2 = HG(DiffPtIdx(EdgeIdx2))  !143
                                ! Trace ray from second edge to terrain endpoint
                                ! Apply reflection analysis for final path segment
                                E2_i2 = DiffPtIdx(EdgeIdx2)  !146
                                NPoints_i2 = INT(NPoints, KIND=I2)  !147
                                CALL REFL(E2_i2, NPoints_i2, PHRF2, HG_at_E2, &  !148
                                          PhaseAtE2, ReflAmpTrace, ReflPhase2, RayHeightOut2, &
                                          AngleOut2, UnusedTotSlant2, MadeItOut, MadeHit)
                                OutputField2 = ReflAmpTrace * AmpAtE2  !151
                                if (MadeItOut) then  !152
                                    ! Accepted ray cleared the profile end; calculate elevation contribution
                                    ! Convert elevation angle to pattern array index
                                    ! Maps to 0.25° bins: idx = angle_deg × 4
                                    ! Apply two-edge diffraction field to elevation pattern
                                    AngleIdx_f2 = (AngleOut2 * 4.0) / DEG2RAD  !156
                                    ! Round to nearest 0.25-degree increment for pattern indexing
                                    AngleIdx2 = NINT(AngleIdx_f2)  !158
                                    ! Check if elevation angle is within valid range for pattern calculation
                                    ! Only 0°…35° are accumulated into the elevation pattern; FOM uses 1°…35°
                                    if (AngleOut2 <= DEG2RAD * 35.0 .AND. AngleOut2 >= 0 .AND. &  !160
                                                                                  UTD_OutMag > UTD_MAG_THRESHOLD) then  !161
                                        TotalDiffCount = TotalDiffCount + 1_I2  !162
                                        ! Apply height-dependent phase correction for antenna position
                                        FinalPhase2 = ReflPhase2 - k * RayHeightOut2 * &  !164
                                                         SIN((AngleIdx2 * DEG2RAD) / 4.0)  !165
                                        ! Add two-edge diffraction contribution to elevation pattern array
                                        E_diffAccum(AngleIdx2) = E_diffAccum(AngleIdx2) &  !167
                                                         + CMPLX(COS(FinalPhase2), SIN(FinalPhase2)) * OutputField2
                                        ! Increment contribution counter for this elevation angle
                                        NCountDiff(AngleIdx2) = &  !170
                                                           NCountDiff(AngleIdx2) + 1_I2  !171
                                        ! Generate debug output for specified elevation angles if enabled
                                        if (DebugEnable == 1 .AND. &  !173
                                            DebugMode == 0) then  !174
                                            ! Output detailed diffraction path information for debugging
                                            if (REAL(AngleIdx2) / 4.0 == DebugExitAngle .AND. &  !176
                                                OutputField2 > 0.1) then  !177
                                                WRITE(4, FMT='(/,"From diff. point ",I2," to ",I2," to end at ",F8.3," deg.  PhiP = ",F8.3)') &
                                                    DiffPtIdx(EdgeIdx1), DiffPtIdx(EdgeIdx2), REAL(AngleIdx2) / 4.0, PhiP / DEG2RAD
                                                WRITE(4, FMT='("Output Field = ",F8.3,"  Phase = ",F11.3," radians, PHRF = ",F8.3)') &
                                                    OutputField2, FinalPhase2, PHRF2
                                            end if
                                        end if
                                    end if
                                end if
                            end if
                        end do
                    end if
                end if
            end do
        end do
    end do

end subroutine ! 203


! ================================================================================
! YUTD: Scalar UTD Diffraction Coefficient Calculation
! ================================================================================
! Purpose: Computes the scalar diffraction coefficient used by the terrain core,
!          using the straight-wedge four-term transition-function form
!
! Theory: Adapted from the edge-diffraction coefficient in:
!         Kouyoumjian, R.G., and Pathak, P.H., "A Uniform Geometrical Theory of
!         Diffraction for an Edge in a Perfectly Conducting Surface", Proc. IEEE
!         62(11), 1448-1461 (1974); this routine forms a scalar coefficient.
!         Four scalar cotangent/F(X) terms and a scalar L normalization are combined;
!         one caller-supplied L_waves value feeds all four transition terms.
!         F(X) is the Fresnel transition function; L_waves is in wavelengths.
!         n is computed here from the Incl argument: n = 2 - Incl/pi.
!
! Input Parameters:
!   FREQ_MHZ - Frequency [MHz]
!   L_waves  - Single distance parameter L used by WD [wavelengths]
!   PhiP - Angular parameter used by WD in PHR +/- PhiP [radians]
!   Incl - Angular parameter used to compute n [radians]
!   PHR      - Scanned angular parameter paired with PhiP [radians]
!
! Output Parameters:
!   OutMag   - UTD coefficient magnitude
!   OutPhase - UTD coefficient phase [radians]
!
! Algorithm:
! 1. Compute n from Incl; WD guards n close to 0.5
! 2. Pass one L_waves value to WD for all transition-function arguments
! 3. Evaluate 4 terms from PHR +/- PhiP and both parities
! 4. Extract mag/phase; complex for coherent summation
!
! ================================================================================
subroutine YUTD ( FREQ_MHZ, L_waves, PhiP, Incl, PHR, OutMag, OutPhase )  !207
    implicit none
    real*4 FREQ_MHZ, L_waves, PhiP, Incl, PHR, OutMag, OutPhase

    real*4 L_param, SinBeta0, n_wedge, LambdaNormFt
    complex*8 UTD_sum, UTD_terms4(1:4)

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    real*4, external :: ATN4

    ! ====================================================================
    ! UTD PARAMETER CALCULATION
    ! ====================================================================
    ! Compute the wavelength factor kept in the normalization algebra
    ! Derive the wedge parameter n from the Incl argument
    LambdaNormFt = 983.84998 / FREQ_MHZ  !229
    n_wedge = 2.0 - Incl / PI  !230

    ! The 2-D terrain profile sets the edge obliquity factor sin(beta0) to 1
    SinBeta0 = 1.0  !233

    ! ====================================================================
    ! UTD COEFFICIENT COMPUTATION VIA WD SUBROUTINE
    ! ====================================================================
    ! Copy the caller's distance parameter, already in wavelengths
    L_param = L_waves  !239
    CALL WD(UTD_terms4, L_param, PHR, PhiP, SinBeta0, n_wedge)  !240

    ! Combine the 4 UTD terms from WD calculation
    ! The signs combine the four angular terms into the diffraction coefficient
    UTD_sum = (UTD_terms4(1) + UTD_terms4(2)) - (UTD_terms4(3) + UTD_terms4(4))  !243

    ! Apply the scalar distance normalization; for positive L the wavelength factors cancel
    UTD_sum = SQRT(LambdaNormFt)*UTD_sum*1.0/SQRT(LambdaNormFt*L_param)  !247
    OutMag = ABS(UTD_sum)  !248

    ! ====================================================================
    ! SPECIAL CASE CORRECTIONS
    ! ====================================================================
    ! Apply the signed PhiP <= 10-degree magnitude correction
    ! This signed test halves the coefficient when PhiP <= 10 deg
    if (PhiP <= DEG2RAD*10.0) then  !254
        OutMag = OutMag / 2.0  !255
    end if
    OutPhase = ATN4(REAL(UTD_sum), AIMAG(UTD_sum))  !257

end subroutine  !259


! ================================================================================
! WD: Scalar UTD Term Calculator with Fresnel Transition Functions
! ================================================================================
! Purpose: Computes the four cotangent/F(X) terms used by YUTD
!          with one L_waves value shared by every transition argument
!
! Theory: Evaluates four cotangent/F(X) terms from PHR +/- PhiP and
!         both parity signs to form the scalar coefficient.
!         The transition function keeps the coefficient finite across
!         the shadow/reflection boundaries used in the angular scan.
!         The final signs and scaling are applied in YUTD.
!
!         Here F(X) is the Fresnel transition function; X_arg is built from
!         the cosine-squared angular factor for each term combination.
!
! Input Parameters:
!   L_waves   - Single distance parameter L [wavelengths]
!   PHR       - Scanned angular parameter paired with PhiP [radians]
!   PhiP - Angular parameter paired with PHR [radians]
!   SinBeta0  - Edge obliquity divisor; 1.0 for this 2-D terrain profile
!   n_wedge   - Wedge parameter computed by YUTD; guarded above 0.5
!
! Output Parameters:
!   UTD_terms4(1:4) - Complex UTD term array for the 4 boundary contributions
!
! ================================================================================
subroutine WD ( UTD_terms4, L_waves, PHR, PhiP, SinBeta0, n_wedge )  !262
    implicit none
    complex*8 UTD_terms4(1:4)
    real*4 L_waves, PHR, PhiP, SinBeta0, n_wedge

    integer*4 term_idx, N_int
    complex*8 WD_scale, WD_const, WD_terms4(1:4)
    real*4 psi_scaled, X_arg, a_pm, delta, frac, parity
    real*4 psi_work, INV_n, TWO_PI_L, MIN_N_MARGIN, INV_TWO_PI

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    complex*8, external :: FFCT

    WD_const = CMPLX(-0.056269769, 0.056269769)  !274
    INV_TWO_PI = 0.15915494  !275

    ! Require n_wedge >= 0.501 before evaluating the cotangent terms
    MIN_N_MARGIN = 0.001  !278
    if (n_wedge - 0.5 >= MIN_N_MARGIN) then  !279
        ! ================================================================
        ! MAIN UTD CALCULATION LOOP FOR 4 BOUNDARY TERMS
        ! ================================================================
        ! Compute parameters for Fresnel transition function evaluation
        TWO_PI_L = TWO_PI * L_waves  !280
        INV_n = 1.0 / n_wedge  !281
        psi_work = PHR - PhiP  !282
        WD_scale = WD_const/(n_wedge*SinBeta0)  !283
        parity = 1.0  !284
        term_idx = 0  !285
        do
            do
                term_idx = term_idx + 1  !286
                ! Calculate argument for Fresnel transition function F(X)
                frac = (psi_work * INV_TWO_PI + parity * 0.5) * INV_n  !287
                N_int = INT(SIGN(0.5, frac) + frac)  !288
                delta = REAL(N_int) * TWO_PI * n_wedge - psi_work  !289
                a_pm = COS(delta*0.5) *  COS(delta*0.5) * 2.0  !290
                X_arg = a_pm * TWO_PI_L  !291
                psi_scaled = psi_work * parity + PI  !292
                if (ABS(X_arg) >= 1e-10) then  !293
                    ! Standard UTD term calculation using FFCT (Fresnel transition function)
                    WD_terms4(term_idx) = FFCT(X_arg) / TAN(psi_scaled * 0.5 * INV_n)  !294
                else
                    ! Special handling for small transition arguments near boundaries
                    WD_terms4(term_idx) = CMPLX(0.0, 0.0)  !296
                    if (ABS(COS(psi_scaled * 0.5 * INV_n)) >= 0.001) then  !297
                        WD_terms4(term_idx) = SIGN(SQRT(TWO_PI_L), psi_scaled) * CMPLX(1.7725, 1.7725)  !298
                        WD_terms4(term_idx) = n_wedge * (WD_terms4(term_idx) - (PI - delta * parity) * TWO_PI_L * CMPLX(0.0, 2.0))  !299
                    end if
                end if
                parity = -parity  !300
                UTD_terms4(term_idx) = WD_scale * WD_terms4(term_idx)  !301
                if (parity >= 0) exit  !302
            end do
            psi_work = PHR + PhiP  !303
            if (term_idx > 3) exit  !304
        end do
    else
        ! ================================================================
        ! WEDGE-PARAMETER LIMIT FOR THIS COEFFICIENT
        ! ================================================================
        ! Set all terms to zero below the implemented n_wedge cutoff
        ! This condition is about wedge geometry, not propagation distance
        do term_idx = 1, 4  !311
            UTD_terms4(term_idx) = CMPLX(0.0, 0.0)  !312
        end do
    end if
end subroutine  !314


! ================================================================================
! FFCT: Fresnel Transition Function for UTD Calculations
! ================================================================================
! Purpose: Computes the complex Fresnel transition function F(X) used in UTD theory
!          to provide smooth transitions between illuminated and shadow regions
!
! Theory: The Fresnel transition function is defined as:
!         F(X) = 2j√X e^(jX) ∫[√X to ∞] e^(-jt²) dt
!
!         This function provides the smooth transition behavior that makes UTD
!         uniform across the geometrical-optics shadow and reflection boundaries.
!         For large |X|, F(X) -> 1 (ordinary GTD limit)
!         For small positive X, F(X) tends to zero with about 45-degree phase
!
! Implementation: Uses piecewise approximation with:
! - Small argument series expansion for |X| < 0.3
! - Table-driven affine approximation for 0.3 < |X| <= 5.5
! - Asymptotic expansion for |X| > 5.5
!
! Input Parameters:
!   X    - Real argument X for transition function
!
! Output:
!   FFCT - Complex Fresnel transition function value F(X)
!
! ================================================================================
complex*8 function FFCT ( X )  !317
    implicit none
    real*4 X

    integer*4 idx
    real*4 Xabs

    real*4, parameter :: TAB_X_BREAKS(1:8) = (/ 0.3, 0.5, 0.69999999, 1.0, 1.5, 2.3, 4.0, 5.5 /)
    complex*8, parameter :: TAB_Y_LOW(1:8) = (/ CMPLX(0.0, 0.0), CMPLX(0.5195, 0.0024999999), CMPLX(0.3355, -0.065499999), CMPLX(0.2187, -0.0757), CMPLX(0.127, -0.068), CMPLX(0.0638, -0.0506), CMPLX(0.024599999, -0.0296), CMPLX(0.0093, -0.0163) /)
    complex*8, parameter :: TAB_Y_HIGH(1:8) = (/ CMPLX(0.5729, 0.26769999), CMPLX(0.6768, 0.2682), CMPLX(0.7439, 0.2549), CMPLX(0.80949998, 0.2322), CMPLX(0.873, 0.1982), CMPLX(0.924, 0.1577), CMPLX(0.96579999, 0.1073), CMPLX(0.9797, 0.0828) /)

    ! ====================================================================
    ! FRESNEL TRANSITION FUNCTION EVALUATION BY ARGUMENT MAGNITUDE
    ! ====================================================================
    ! Three-region implementation used by this approximation:
    ! Region 1: Small arguments (series expansion)
    ! Region 2: Medium arguments (table-driven affine approximation)
    ! Region 3: Large arguments (asymptotic expansion)

    Xabs = ABS(X)  !333
    if (Xabs <= 5.5) then  !334
        if (Xabs <= 0.3) then !335
            ! Small-argument approximation; leading real/imag parts scale as sqrt(X)
            ! The expression tends to zero and then rotates through the transition
            FFCT = EXP(CMPLX(0.0*Xabs, 1.0*Xabs)) * CMPLX(1.253*SQRT(Xabs) - 0.6667*Xabs*Xabs, 1.253*SQRT(Xabs) - 2.0*Xabs)  !336
        else
            ! Medium argument range: use table values with affine extrapolation
            do idx = 2, 7  !338
                if (Xabs < TAB_X_BREAKS(idx)) exit  !339
            end do
            FFCT = (Xabs - TAB_X_BREAKS(idx)) * TAB_Y_LOW(idx) + TAB_Y_HIGH(idx)  !340
        end if
    else
        ! Large argument asymptotic expansion: F(X) -> 1 - 0.75/X**2 + j(0.5/X)
        ! This is the transition-function limit used away from boundaries
        FFCT = CMPLX(-(0.75/Xabs)/Xabs + 1.0, 0.5/Xabs)  !342
    end if
    ! Handle negative arguments using symmetry property: F(-X) = F*(X)
    if (X < 0.0) then  !344
        FFCT = CONJG(FFCT)  !345
    end if

end function  !347


! ================================================================================
! ATN4: Quadrant-Aware Arctangent Helper
! ================================================================================
! Purpose: Computes the program's arctangent angle with explicit quadrant
!          handling, including zero arguments and the X+Y branch test
!
! The positive-atan branch subtracts pi when X+Y < 0.0; the negative-atan
! branch adds pi when X < 0.0.
!
! Input Parameters:
!   X    - X component (cosine-like term)
!   Y    - Y component (sine-like term)
!
! Output:
!   ATN4 - Angle in radians, roughly in range [-π, π]
!
! ================================================================================
real*4 function ATN4 ( X, Y )  !350
    implicit none
    real*4 X, Y

    real*4 PI

    PI = 3.1415927  !354
    if (X == 0.0) then  !355
        if (Y /= 0.0) then  !356
            ATN4 = PI*0.5*Y/ABS(Y)  !357
            return  !358
        else
            ATN4 = 0.0  !360
            return  !361
        end if
    else
        ATN4 = ATAN(Y/X)  !364
        if (ATN4 < 0.0) then  !365
            if (X < 0.0) then  !366
                ATN4 = PI + ATN4  !367
                return  !368
            end if
        else
            if (X + Y < 0.0) then  !371
                ATN4 = ATN4 - PI  !372
                return  !373
            end if
        end if
    end if

end function  !378


! ================================================================================
! FRESNEL: Plane-Wave Ground Reflection Coefficient Calculator
! ================================================================================
! Purpose: Computes the horizontal-polarization Fresnel coefficient for a
!          plane wave reflecting from lossy ground using complex permittivity
!
! Theory: Uses the supplied angle in the horizontal Fresnel coefficient form:
!         Gamma_h(a)=(sin a - sqrt(eps_r-cos^2 a))/(sin a + sqrt(...))
!         eps_r = eps' - j*sigma/(omega*eps0) is complex permittivity
!         ε' = relative permittivity, σ = conductivity [S/m]
!
! Input Parameters:
!   FresnelAngle - Angle argument a [radians]; code uses ABS(a) directly
!   AmpIn        - Field amplitude before reflection
!   PhaseIn      - Phase before reflection [radians]
!
! Output Parameters:
!   AmpOut       - Field amplitude after reflection (amplitude × |Γ_h|)
!   PhaseOut     - Phase after reflection [radians] (phase + arg(Γ_h))
!
! ================================================================================
subroutine FRESNEL ( FresnelAngle, AmpIn, PhaseIn, AmpOut, PhaseOut )  !381
    implicit none
    real*4 FresnelAngle, AmpIn, PhaseIn, AmpOut, PhaseOut

    real*4 Gamma_arg, Gamma_mag, den_arg, den_abs, den_imag, den_real, num_arg, num_abs, num_imag
    real*4 num_real, phi_over2, sqrt_eps_mag, eps_imag_term, eps_minus_cos2

    real*4 DG(0:150), HG(0:150), FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE
    common /Params/ DG, HG, FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE

    real*4, external :: ATN4

    ! ====================================================================
    ! COMPLEX PERMITTIVITY CALCULATION FOR SOIL
    ! ====================================================================
    ! Compute complex relative permittivity: eps_r = eps' - j*sigma/(omega*eps0)
    ! Uses global soil permittivity and conductivity [S/m] from the common block

    eps_minus_cos2 = SOIL_EPSR - COS(ABS(FresnelAngle))*COS(ABS(FresnelAngle))  !396
    eps_imag_term = -((SOIL_COND_PARAM * 18000.0) / FREQ_MHZ)  !397
    sqrt_eps_mag = SQRT(SQRT(eps_imag_term*eps_imag_term + eps_minus_cos2*eps_minus_cos2))  !398
    phi_over2 = ATN4(eps_minus_cos2, eps_imag_term) / 2.0  !399
    num_real = SIN(ABS(FresnelAngle)) - COS(phi_over2)*sqrt_eps_mag  !400
    num_imag = -(SIN(phi_over2)*sqrt_eps_mag)  !401
    num_abs = SQRT(num_imag*num_imag + num_real*num_real)  !402
    num_arg = ATN4(num_real, num_imag)  !403
    den_real = COS(phi_over2)*sqrt_eps_mag + SIN(ABS(FresnelAngle))  !404
    den_imag = SIN(phi_over2)*sqrt_eps_mag  !405
    den_abs = SQRT(den_real*den_real + den_imag*den_imag)  !406
    den_arg = ATN4(den_real, den_imag)  !407
    Gamma_mag = num_abs / den_abs  !408
    Gamma_arg = num_arg - den_arg  !409
    AmpOut = Gamma_mag * AmpIn  !410
    PhaseOut = Gamma_arg + PhaseIn  !411

end subroutine !413


! ================================================================================
! ANGIN: UTD Angular Parameter Calculator
! ================================================================================
! Purpose: Computes angular parameters needed by the diffraction coefficient,
!          including Incl/PhiP values and scan sectors
!
! Theory: Converts terrain segment angles and incident ray angle into
!         Incl/PhiP/PHR parameters used by the scalar UTD coefficient.
!         Incl sets n in YUTD; PhiP is paired with PHR in WD.
!
! Input Parameters:
!   Slpe1     - Terrain slope angle 1 [radians]
!   Slpe2     - Terrain slope angle 2 [radians]
!   Incidence - Incident ray angle [radians]
!
! Output Parameters:
!   Incl - Angular parameter later used to compute n [radians]
!   PhiP - Angular parameter passed to WD [radians]
!   PHR  - Starting observation/scan angle [radians]
!   NSteps      - Number of 0.25-degree scan steps
!
! ================================================================================
subroutine ANGIN ( Slpe1, Slpe2, Incidence, Incl, PhiP, PHR, NSteps )  !416
    implicit none
    real*4 Slpe1, Slpe2, Incidence, Incl, PhiP, PHR
    integer*4 NSteps

    real*4 PHR_start

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    if (Slpe1 < 0.0) then  !420
        Incl = ABS(Slpe1) + PI + Slpe2  !421
    else
        ! Slpe1 >= 0 branch of the Incl-parameter mapping
        Incl = PI - ABS(Slpe1) + Slpe2  !424
    endif

    PhiP = Slpe1 - Incidence  !427

    ! ====================================================================
    ! UTD ANGULAR SECTOR CALCULATION
    ! ====================================================================
    ! Determine the angular range and step size for the coefficient scan
    ! This sets up the observation-angle sweep used by caller loops
    ! Calculate ending observation angle for the scan
    ! Set angular range based on terrain geometry branches
    ! Determine sweep limits for diffraction coefficient evaluation
    ! Apply angular offset for UTD transition region coverage
    PHR = TWO_PI - Incl - DEG2RAD * 0.25  !434

    ! Adjust angular range using the adjacent-slope ordering
    ! Select appropriate observation angle limits for diffraction analysis
    if (Slpe2 > Slpe1) then  !438
        ! Slpe2 > Slpe1 branch - start 30 degrees below the ending PHR
        PHR_start = TWO_PI - Incl - DEG2RAD*30.0  !440
    else
        ! Slpe2 <= Slpe1 branch - start from the PhiP-based offset
        ! Uses PhiP as the offset for the scan start
        PHR_start = PI - PhiP - DEG2RAD*10.0  !444
    end if

    ! Calculate number of 0.25-degree angular scan steps
    NSteps = INT(4.0*ABS(PHR/DEG2RAD - PHR_start/DEG2RAD))  !448

end subroutine !450


! ================================================================================
! ANGHORIZ: Absolute Ray-Angle Mapper for REFL
! ================================================================================
! Purpose: Converts the local post-diffraction angle used by UTD scans into
!          the absolute ray angle expected by REFL
!
! Theory: Applies the terrain-slope angle mapping before ray tracing.
!         The result is an absolute elevation/ray angle, not a horizon distance.
!         Fresnel reflection is applied later inside REFL if a terrain hit occurs.
!
! Input Parameters:
!   Slpe             - Terrain slope angle [radians]
!   LocalPHR         - Local post-diffraction scan angle [radians]
!
! Output Parameters:
!   PHRF             - Absolute ray/elevation angle [radians]
!
! ================================================================================
subroutine ANGHORIZ( Slpe, LocalPHR, PHRF )  !453
    implicit none
    real*4 Slpe, LocalPHR, PHRF

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    if (Slpe < 0.0) then  !457
        ! Slpe < 0 branch of the angle mapping
        PHRF = PI - (ABS(Slpe) + LocalPHR)  !459
    else
        ! Slpe >= 0 branch of the angle mapping
        PHRF = PI - (LocalPHR - ABS(Slpe))  !462
    end if

end subroutine  !465



! ================================================================================
! DRD: Diffraction-Reflection-Diffraction Path Calculator
! ================================================================================
! Purpose: Searches DRD paths when the ProcessFlag == 0 branch calls this pass
!          YTWCore1 initializes ProcessFlag = 1, so HFTA GUI runs skip this pass
!
! Theory: Implements cascaded propagation using:
!         1. UTD diffraction at first edge (antenna → edge1)
!         2. Geometrical-optics ray search from edge1 through ground reflection to edge2
!         3. UTD diffraction at second edge, then final REFL trace
!
!         The middle leg contributes traced slant distance; final REFL supplies accumulated amplitude/phase.
!
! Algorithm: For each antenna element and edge pair, when entered:
! - Search for a DRD path using iterative ray shooting
! - Apply UTD at first diffraction edge
! - Trace reflected middle-leg geometry
! - Apply UTD at second diffraction edge
! - Accumulate coherently in elevation pattern
!
! Input Parameters:
!   NPoints        - Number of terrain points
!   NDiffPoints    - Number of diffraction edges
!   NElements      - Number of antenna elements
!   DebugEnable    - Debug output enable flag
!   DebugMode      - Debug mode selector
!   DebugExitAngle - Debug elevation angle
!   AntPhase       - Antenna phase array (not read by this routine)
!
! Output Parameters:
!   E_diffAccum    - Complex elevation pattern array (DRD additions if entered)
!
! ================================================================================
subroutine DRD ( NPoints, NDiffPoints, NElements, DebugEnable, DebugMode, DebugExitAngle, AntPhase, E_diffAccum ) !469
    implicit none
    integer*4 NPoints, NDiffPoints, NElements, DebugEnable, DebugMode
    real*4 DebugExitAngle
    integer*2 AntPhase(*)
    complex*8 E_diffAccum(0:181)

    integer*2 e1_i2, e2_i2, e1_i2_fine, e2_i2_fine, e1_i2_micro, e2_i2_micro, e2_i2_final, NPoints_i2
    integer*4 ElemIdx, EdgeIdx1, EdgeIdx2, NStepsScan, ScanStepIdx, IterCountFine, IterIdxFine, MicroIterIdx, NSteps2, StepIdx2, AngleIdx
    real*4 HtRay_curr, Edge12Angle, Slpe1_e1, Slpe2_e1, UnusedStartScanAngle, AngleStep, ScanAngle, ReflPhaseIn, ReflAmp, ReflPhase, SlantDist_e1e2_ft, AngleOut
    real*4 HtRay_prev, DeltaHtRay, ElemGain, PhaseToE1Rad, L1_waves, AInclA, PhiP, PHR, UTD_OutMag, UTD_OutPhase, AmpAfterE1, PhaseAfterE1
    real*4 Slpe1_e2, Slpe2_e2, L2Residual_waves, UnusedPhaseAtE2, AmpAtE2, UnusedDRDZero, PHRF2, HG_at_E2, ReflPhaseFinal, PhaseBeforeFinalRefl, AngleIdx_f, UnusedHtRayFinal, UnusedFinalPhase
    logical FoundDRDPath, MadeItOut, MadeHit

    integer*2 DiffPtIdx(1:200), EdgePairUsed(1:200, 1:200), NCountDiff(0:180), TotalDiffCount
    real*4 DiffPh0(1:4, 1:200), FAngle(1:4, 1:200)
    common /Globals/ DiffPtIdx, EdgePairUsed, NCountDiff, TotalDiffCount, DiffPh0, FAngle

    real*4 DG(0:150), HG(0:150), FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE
    common /Params/ DG, HG, FREQ_MHZ, SOIL_EPSR, SOIL_COND_PARAM, k, LAMBDA_FT, PATTERN_ELEV_NORM60_OVER_BW, ARRAY_PATTERN_SCALE

    real*4 PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT
    common /Constants/ PI, TWO_PI, UTD_MAG_THRESHOLD, DEG2RAD, HALF_PI, EARTH_RADIUS_FT

    real*4, external :: ATN4

    integer, parameter :: I2 = selected_int_kind(4)

    if (.false.) AntPhase(1) = 0  ! suppress unused dummy argument warning

    if (DebugEnable == 1) then  !502
        WRITE(4, *) ' '  !503
        WRITE(4, FMT='("Starting Diff.-Refl.-Diff. Analysis",/)')  !504
    end if

    ! MAIN DRD EDGE-PAIR PROCESSING LOOP
    do ElemIdx = 1, NElements  !508
        FoundDRDPath = .false.  !509
        do EdgeIdx1 = 1, NDiffPoints  !510
            ! Process each ordered pair of diffraction edges
            ! Check combinations of first and second diffraction edges
            ! Apply the path tests used by this DRD search
            ! Reject adjacent edge indices before ray shooting
            do EdgeIdx2 = EdgeIdx1 + 1, NDiffPoints  !515
                if (DiffPtIdx(EdgeIdx2) - DiffPtIdx(EdgeIdx1) == 1) then  !516
                    CYCLE
                end if  !518
                if (EdgePairUsed(DiffPtIdx(EdgeIdx1) + 1, DiffPtIdx(EdgeIdx2)) == 0) then  ! WARNING: inconsistent bounds check in Assembly code  !519
                    ! No recorded edge-pair continuation - skip this combination
                    ! Try the next non-adjacent pair of diffraction edges
                    CYCLE  !522
                end if
                if (EdgeIdx2 < NDiffPoints) then  !524
                    ! Calculate the straight angle from first edge to second edge
                    ! This initializes the launch scan for the reflected middle leg
                    ! The actual trace is still tested by REFL below
                    ! Terrain blocking/reflection is handled by that trace
                    ! Store the angle used to start the scan
                    ! Prepare the candidate inter-edge geometry
                    Edge12Angle = ATN4(DG(DiffPtIdx(EdgeIdx2)) - DG(DiffPtIdx(EdgeIdx1)), HG(DiffPtIdx(EdgeIdx2)) - HG(DiffPtIdx(EdgeIdx1)))  !531
                else
                    HtRay_curr = 0.0  !534
                    CYCLE  !535
                end if
                ! REFLECTION ANALYSIS SETUP FOR DRD PATH
                ! Compute adjacent segment angles at the first edge
                ! These angles drive the scan and later first-edge UTD setup
                ! Extract gradients used to compute local incidence angles
                ! Check geometric constraints for candidate DRD paths
                ! Set up angles for the REFL ray-tracing search
                ! Prepare for iterative search of a reflection point
                ! Initialize launch parameters with local terrain tilt
                ! Use local straight-segment geometry for the reflected-leg search
                ! Set angular limits for reflection calculations
                Slpe1_e1 = ATN4(DG(DiffPtIdx(EdgeIdx1)  ) - DG(DiffPtIdx(EdgeIdx1)-1), &  !547
                                      HG(DiffPtIdx(EdgeIdx1)  ) - HG(DiffPtIdx(EdgeIdx1)-1))  !548
                Slpe2_e1 = ATN4(DG(DiffPtIdx(EdgeIdx1)+1) - DG(DiffPtIdx(EdgeIdx1)  ), &  !549
                                      HG(DiffPtIdx(EdgeIdx1)+1) - HG(DiffPtIdx(EdgeIdx1)  ))
                ! Set up angular search parameters for reflection point iteration
                UnusedStartScanAngle = DEG2RAD * 0.25 + Slpe2_e1  !552
                NStepsScan = INT(4.0 * ABS(Edge12Angle/DEG2RAD - Slpe2_e1/DEG2RAD))  !553
                AngleStep = -(DEG2RAD * 0.25)  !554
                ! Initialize ray height for reflection search algorithm
                ScanAngle = Edge12Angle  !556
                ! Step the launch angle until one edge-to-edge trace is accepted
                ! REFL supplies height, angle, slant distance, and hit flags
                ! Each step advances the trial angle by AngleStep
                Loop_DRD_ReflectionScan: do ScanStepIdx = 1, NStepsScan  !560
                    ScanAngle = AngleStep + ScanAngle  !561
                    e1_i2 = DiffPtIdx(EdgeIdx1)  !562
                    e2_i2 = DiffPtIdx(EdgeIdx2)  !563
                    CALL REFL(e1_i2, e2_i2, ScanAngle, HG(DiffPtIdx(EdgeIdx1)), &  !564
                              ReflPhaseIn, ReflAmp, ReflPhase, HtRay_curr, AngleOut, SlantDist_e1e2_ft, &
                              MadeItOut, MadeHit)
                    ! Check reflection path results and debug output
                    ! Validate ray tracing success for DRD path segment
                    if (DebugEnable == 1) then  !568
                        WRITE(4, FMT='("From ", I2, " to ", I2, ", HtRay = ", F8.3, "  HG = ", F8.3, "  MadeItOut = ", I2, "  MadeHit = ", I2, "  FAngle = ", F8.3)') &  !569
                              DiffPtIdx(EdgeIdx1), &
                              DiffPtIdx(EdgeIdx2), &
                              HtRay_curr, &
                              HG(DiffPtIdx(EdgeIdx2)), &
                              MadeItOut, &
                              MadeHit, &
                              FAngle(ElemIdx, DiffPtIdx(EdgeIdx1)) / DEG2RAD
                    end if
                    ! Fine-tune reflection search if the trace ends near edge 2
                    if ((.not. MadeItOut) &  !579
                        .and. ABS(HtRay_curr - HG(DiffPtIdx(EdgeIdx2))) < 10.0) then
                        ! Reduce angular step size for precision convergence
                        ! Switch to fine-grain search mode near the second edge
                        AngleStep = DEG2RAD * 0.01  !583
                        ! Store initial ray height for convergence tracking
                        HtRay_prev = HtRay_curr  !585
                        ! Initialize fine-search iteration counter
                        ! Begin precision reflection point determination
                        IterCountFine = 1  !588
                        do IterIdxFine = 1, NStepsScan + 200  !589
                            ScanAngle = AngleStep + ScanAngle  !590
                            e1_i2_fine = DiffPtIdx(EdgeIdx1)  !591
                            e2_i2_fine = DiffPtIdx(EdgeIdx2)  !592
                            CALL REFL(e1_i2_fine, e2_i2_fine, ScanAngle, HG(DiffPtIdx(EdgeIdx1)), &  !593
                                      ReflPhaseIn, ReflAmp, ReflPhase, HtRay_curr, &
                                      AngleOut, SlantDist_e1e2_ft, MadeItOut, MadeHit)
                            ! Track convergence progress for adaptive step control
                            if (IterCountFine == 50) then  !597
                                DeltaHtRay = ABS(HtRay_curr - HtRay_prev)  !598
                            end if
                            if (IterCountFine == 51 &  !600
                                .and. DeltaHtRay < ABS(HtRay_curr - HtRay_prev)) then  !601
                                ! Reverse search direction if diverging from edge 2
                                AngleStep = -(AngleStep * 1.0)  !603
                            end if
                            ! Ultra-fine search if close to edge 2 but not converged
                            ! Apply micro-step refinement for final convergence
                            if ((.not. MadeItOut) &  !607
                                .and. ABS(HtRay_curr - HG(DiffPtIdx(EdgeIdx2))) < 1.0) then  !608
                                AngleStep = AngleStep * 0.1  !609
                                do MicroIterIdx = 1, 100  !610
                                    ScanAngle = AngleStep + ScanAngle  !611
                                    e1_i2_micro = DiffPtIdx(EdgeIdx1)  !612
                                    e2_i2_micro = DiffPtIdx(EdgeIdx2)  !613
                                    call REFL(e1_i2_micro, e2_i2_micro, ScanAngle, HG(DiffPtIdx(EdgeIdx1)), &  !614
                                              ReflPhaseIn, ReflAmp, ReflPhase, HtRay_curr, &
                                              AngleOut, SlantDist_e1e2_ft, MadeItOut, MadeHit)
                                    if (MadeItOut &  !617
                                        .and. ABS(HtRay_curr - HG(DiffPtIdx(EdgeIdx2))) < 0.1) then  !618
                                        if (DebugEnable == 1) then  !619
                                            WRITE(4, FMT='("    From ", I2, " to ", I2)') &  !620
                                                  DiffPtIdx(EdgeIdx1), DiffPtIdx(EdgeIdx2)
                                        end if
                                        FoundDRDPath = .true.  !623
                                        EXIT Loop_DRD_ReflectionScan  !624
                                    end if
                                    FoundDRDPath = .false.  !626
                                end do
                            end if
                        end do
                    end if
                end do Loop_DRD_ReflectionScan
                ! DRD RAY SEARCH COMPLETED - process any accepted path
                ! Apply first-edge UTD coefficient and antenna pattern factor
                ! Convert the stored first-edge phase into an L_waves proxy
                ! Later subtract that proxy from the reflected middle-leg distance
                ! Combine UTD coefficients with geometric factors
                ! Account for antenna element directivity patterns
                ! Set up parameters for final field accumulation
                ! Add accepted DRD contribution to the diffraction accumulator
                if (FoundDRDPath) then  !640
                    FoundDRDPath = .false.  !641
                    ! Apply antenna pattern factor for current element and edge
                    ElemGain = COS(PATTERN_ELEV_NORM60_OVER_BW * FAngle(ElemIdx, DiffPtIdx(EdgeIdx1))) * ARRAY_PATTERN_SCALE  !643
                    ! Get total phase from antenna to first diffraction edge
                    PhaseToE1Rad = DiffPh0(ElemIdx, DiffPtIdx(EdgeIdx1))  !645
                    ! Convert phase to normalized path length for UTD calculation
                    L1_waves = (PhaseToE1Rad / k) / LAMBDA_FT  !647
                    ! Set up the first-edge coefficient for the DRD cascade
                    ! ANGIN builds the Incl/PhiP/PHR tuple from local slopes
                    ! FAngle supplies the incident angle stored for this edge
                    ! This coefficient multiplies the antenna pattern factor
                    ! Its output becomes the incident field for the second edge
                    ! ScanAngle then selects the inter-edge outgoing direction
                    CALL ANGIN(Slpe1_e1, Slpe2_e1, FAngle(ElemIdx, DiffPtIdx(EdgeIdx1)), &  !654
                        AInclA, PhiP, PHR, NSteps2)
                    ! Override PHR with the inter-edge outgoing direction
                    ! This selects the first-edge coefficient for ScanAngle
                    if (Slpe1_e1 < 0.0) then  !657
                        PHR = PI - ScanAngle - ABS(Slpe1_e1)  !658
                    else
                        PHR = ABS(Slpe1_e1) + PI - ScanAngle !660
                    end if
                    CALL YUTD(FREQ_MHZ, L1_waves, PhiP, AInclA, PHR, UTD_OutMag, UTD_OutPhase)  !662
                    AmpAfterE1 = UTD_OutMag * ElemGain  !663
                    PhaseAfterE1 = (PhaseToE1Rad - UTD_OutPhase) &  !668
                                   + (SlantDist_e1e2_ft - LAMBDA_FT * L1_waves) * k  !669
                    ! Compute slopes at the second edge for the next YUTD call
                    Slpe1_e2 = ATN4(DG(DiffPtIdx(EdgeIdx2)  ) - DG(DiffPtIdx(EdgeIdx2)-1), &  !671
                                          HG(DiffPtIdx(EdgeIdx2)  ) - HG(DiffPtIdx(EdgeIdx2)-1))  !672
                    Slpe2_e2 = ATN4(DG(DiffPtIdx(EdgeIdx2)+1) - DG(DiffPtIdx(EdgeIdx2)), &  !673
                                          HG(DiffPtIdx(EdgeIdx2)+1) - HG(DiffPtIdx(EdgeIdx2)))
                    ! Set up second-edge Incl/PhiP parameters
                    ! Calculate angular scan limits for second edge
                    ! Prepare the second-edge outgoing diffraction scan
                    ! Apply terrain geometry constraints for second edge processing
                    CALL ANGIN(Slpe1_e2, Slpe2_e2, ScanAngle, AInclA, &  !679
                               PhiP, PHR, NSteps2)
                    ! Apply second-edge UTD processing for DRD completion
                    ! Build the residual second-edge distance parameter in wavelengths
                    ! Use that value through the second-edge angular scan
                    ! Keep the same residual value for each PHR step in this pair
                    L2Residual_waves = SlantDist_e1e2_ft / LAMBDA_FT - L1_waves  !685
                    AngleStep = -(DEG2RAD * 0.25)  !686
                    do StepIdx2 = 1, NSteps2  !687
                        AmpAtE2 = AmpAfterE1  !688
                        UnusedPhaseAtE2 = PhaseAfterE1  !689
                        PHR = AngleStep + PHR  !690
                        UnusedDRDZero = 0.0  !691
                        CALL YUTD(FREQ_MHZ, L2Residual_waves, PhiP, AInclA, &  !692
                                  PHR, UTD_OutMag, UTD_OutPhase)
                        if (UTD_OutMag >= UTD_MAG_THRESHOLD) then  !694
                            AmpAtE2 = UTD_OutMag * AmpAtE2  !695
                            PhaseBeforeFinalRefl = PhaseAfterE1 - UTD_OutPhase  !696
                            CALL ANGHORIZ(Slpe1_e2, PHR, PHRF2)  !697
                            ! Calculate final propagation angle from the second edge
                            ! Validate geometry for final ray tracing segment
                            HG_at_E2 = HG(DiffPtIdx(EdgeIdx2))  !700
                            ! Trace final ray segment from second edge to terrain endpoint
                            ! REFL may add a final reflected-leg amplitude and phase
                            ! Validate final ray tracing success and geometry
                            e2_i2_final = DiffPtIdx(EdgeIdx2)  !704
                            NPoints_i2 = INT(NPoints, KIND=I2)  !705
                            CALL REFL(e2_i2_final, NPoints_i2, PHRF2, HG_at_E2, &  !706
                                      PhaseBeforeFinalRefl, ReflAmp, ReflPhaseFinal, HtRay_curr, &
                                      AngleOut, SlantDist_e1e2_ft, MadeItOut, MadeHit)
                            PHRF2 = AngleOut  !709
                            AmpAtE2 = ReflAmp * AmpAtE2  !710
                            if (MadeItOut) then  !711
                                ! DRD path reached profile end - process elevation-bin contribution
                                ! Convert final elevation angle to pattern array index
                                ! Maps to 0.25° bins: idx = angle_deg × 4
                                ! Apply height corrections for antenna position
                                AngleIdx_f = (AngleOut * 4.0) / DEG2RAD  !715
                                ! Round to nearest 0.25-degree pattern array index
                                AngleIdx = NINT(AngleIdx_f) !717
                                ! Calculate total phase including all path segments and height effects
                                ReflPhase = ReflPhaseFinal - k * HtRay_curr * &  !719
                                                 SIN((AngleIdx * DEG2RAD) / 4.0)  !720
                                ! Validate angle and field before adding the sine/cosine DRD phasor
                                ! Check output angle and field threshold before inclusion
                                ! DRD uses 0°…30° accumulation when this branch is entered
                                if (PHRF2 > 0.0 .and. PHRF2 <= DEG2RAD * 30.0 &  !723
                                    .and. AmpAtE2 > UTD_MAG_THRESHOLD) then  !724
                                    TotalDiffCount = TotalDiffCount + 1_I2  !725
                                    E_diffAccum(AngleIdx) = E_diffAccum(AngleIdx) &  !726
                                                     + CMPLX(SIN(ReflPhase), COS(ReflPhase)) * AmpAtE2
                                    NCountDiff(AngleIdx + 1) = &  !729
                                            NCountDiff(AngleIdx + 1) + 1_I2  !730
                                    ! Generate debug output for DRD path analysis if enabled
                                    if (DebugEnable == 1) then  !732
                                        if (DebugMode == 0) then  !733
                                            if (REAL(AngleIdx) / 4.0 == DebugExitAngle) then  !734
                                                    WRITE(4, FMT='(/,"From diff. point ", I2, " to ", I2, " to end post at ", F8.3, " deg.")') &  !735
                                                          DiffPtIdx(EdgeIdx1), &
                                                          DiffPtIdx(EdgeIdx2), &
                                                          REAL(AngleIdx) / 4.0
                                                    WRITE(4, FMT='("PhiP=", F8.3, " AInclA=", F8.3, " PHR=", F8.3, " OutMag=", F8.3, " OutPhase=", F8.3)') &  !743
                                                          PhiP / DEG2RAD, &
                                                          AInclA / DEG2RAD, &
                                                          PHR / DEG2RAD, &
                                                          UTD_OutMag, &
                                                          UTD_OutPhase / DEG2RAD
                                                    WRITE(4, FMT='(" DiffPh0(", I1, ",", I2, ") = ", F8.3)') &  !751
                                                          ElemIdx, &
                                                          DiffPtIdx(EdgeIdx1), &
                                                          DiffPh0(ElemIdx, DiffPtIdx(EdgeIdx1))
                                                    WRITE(4, FMT='("Distance in wavelengths = ", F11.3)') &  !754
                                                          L1_waves
                                                    WRITE(4, FMT='("Out field = ", F8.3, "  PhaseOut = ", F8.3, "  FAngle = ", F8.3, " NCountDiff = ", I4)') &  !756
                                                          AmpAtE2, &
                                                          ReflPhase, &
                                                          FAngle(ElemIdx, DiffPtIdx(EdgeIdx1)) / DEG2RAD, &
                                                          NCountDiff(AngleIdx + 1)
                                            end if
                                        else
                                            WRITE(4, *) 'Did not make it.'  !764
                                            WRITE(4, FMT='(/,"From diff. point ", I2, " to ", I2)') & !765
                                                  DiffPtIdx(EdgeIdx1), &
                                                  DiffPtIdx(EdgeIdx2)
                                            WRITE(4, FMT='("PhiP=", F8.3, " AInclA=", F8.3, " PHR=", F8.3, " OutMag=", F8.3, " OutPhase=", F8.3)') &  !766
                                                  PhiP / DEG2RAD, &
                                                  AInclA / DEG2RAD, &
                                                  PHR / DEG2RAD, &
                                                  UTD_OutMag, &
                                                  UTD_OutPhase / DEG2RAD
                                        end if
                                    end if
                                end if
                            end if
                        end if
                    end do
                end if
            end do
        end do
    end do
end subroutine
