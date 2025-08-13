## COMMON /Constants/

 * 100187a0 -> float PI
 * 100187a4 -> float TWO_PI
 * 100187a8 -> float DEG2RAD
 * 100187ac -> float HALF_PI
 * 10012200 -> float EARTH_RADIUS_FT
 * 1002e150 -> float UTD_MAG_THRESHOLD

## COMMON /Params/

 * 1002c1e0 -> float DG(0:150)
 * 1002c43c -> float HG(0:150)
 * 100187c8 -> float FREQ_MHZ
 * 100187c0 -> float SOIL_EPSR
 * 100187c4 -> float SOIL_COND_PARAM
 * 100187d4 -> float k
 * 100187d8 -> float LAMBDA_FT
 * 100187cc -> float PATTERN_ELEV_NORM60_OVER_BW
 * 100187d0 -> float ARRAY_PATTERN_SCALE

## COMMON /Globals/

 * 1002c6be -> short DiffPtIdx(1:200)
 * 100187ba -> short EdgePairUsed(1:200, 1:200)
 * 100187e2 -> short NCountDiff(0:180)
 * 100187e0 -> short TotalDiffCount
 * 1002c83c -> float DiffPh0(1:4, 1:200)
 * 1002d4bc -> float FAngle(1:4, 1:200)

## subroutine YTWCore1 (args)

 * a1 -> float DG0_in(0:150)
 * a2 -> float HG0_in(0:150)
 * a3 -> float HantFeetIn(0:3)
 * a4 -> float FREQ_MHZ_in
 * a5 -> float SOIL_EPSR_in
 * a6 -> float SOIL_COND_PARAM_in
 * a7 -> short AntPatternType
 * a8 -> short DiffractionDisable
 * a9 -> short DebugEnable_in
 * a10 -> float DebugExitAngle_in
 * a11 -> float Pattern_dB(0:139)
 * a12 -> short AntPhase(0:3)

## subroutine YTWCore1 (locals)

 * 1001222c -> int M
 * 100121d0 -> float ASlp1
 * 100121cc -> float ASlp2
 * 100121c8 -> float SegLenFt
 * 100134ee -> short IsDiffPoint(1:200)
 * 10012238 -> short NDiffPoints
 * 10012240 -> short NPointsSmoothed_i2
 * 10012244 -> short M_i2
 * 10012248 -> short RDPoint_i2
 * 100121f4 -> int ScanIdx
 * 100121f0 -> int LastPointIdx
 * 10012228 -> int KeepIdx
 * 100121e0 -> int NPointsSmoothed
 * 10012214 -> float PatternBeamwidthDeg
 * 10012210 -> float AntPatternGainFactor
 * 100121dc -> int NElements
 * 100121d8 -> float NElements_f
 * 100121d4 -> float InvSqrtN
 * 1001220c -> int DebugEnable
 * 10012208 -> float DebugExitAngle
 * 10012204 -> int DebugMode
 * 100121fc -> int ProcessFlag
 * 1002c694 -> float HantFeetAbs(1:4)
 * 1001848c -> float RayHeightAtAngle(-220:180)
 * 10014950 -> float SlantSegFt(-220:180)
 * 100175c8 -> float ElemPatternAmp(1:4,-220:180)
 * 100159e0 -> float ElemPhase(1:4,-220:180)
 * 10013d5e -> short AngleIdxByElemLaunch(1:4,-220:180)
 * 10012828 -> complex E_total_tmp(0:181)
 * 10012dd8 -> complex E_diffAccum(0:181)
 * 10012278 -> complex E_goAccum(0:181)
 * 10014308 -> float PatternMag(0:181)
 * 10016534 -> float UnusedPatternSmoothed(0:181)
 * 100121c0 -> float LaunchAngle
 * 100121bc -> float RayHeightCurrent
 * 100121b8 -> float HtRay
 * 100121b4 -> float PhaseToM
 * 100121b0 -> float AntEdgeDistWaves
 * 100121ac -> float ElemGain
 * 100121a8 -> float Incl
 * 100121a4 -> float PhiP
 * 100121a0 -> float PHR
 * 10012198 -> float PHRStepNeg0p25
 * 1001219c -> int NSteps
 * 10012194 -> float UnusedUTDZero
 * 10012190 -> float UTD_OutMag
 * 1001218c -> float UTD_OutPhase
 * 10012188 -> float OutputField
 * 10012184 -> float PhaseWork
 * 10012180 -> float PHRF
 * 1001217c -> float HG_at_M
 * 10012178 -> float ReflAmp
 * 10012174 -> float ReflPhase
 * 10012170 -> float PHRout
 * 1001216c -> float TotSlantFt
 * 10012168 -> bool MadeItOut
 * 10012164 -> bool MadeHit
 * 10012160 -> float AngleIdx_f
 * 10012220 -> int AngleIdx
 * 1001215c -> float FinalPhase
 * 100121c4 -> int ElemIdx
 * 10012150 -> int LaunchIdxQ
 * 1001214c -> float AngleOutRad
 * 10012230 -> int Ipt
 * 10012148 -> int FoundRD
 * 10012154 -> int RDHitIdx
 * 10012144 -> float SegmentSlope
 * 10012140 -> float ReflectOffset
 * 1001213c -> float ReflectPointDistFt
 * 10012138 -> float ReflectPointHeightFt
 * 10012134 -> float SegmentAngleRad
 * 10012130 -> float ElemPatternAmp_curr
 * 1001212c -> float ReflGain
 * 10012128 -> float ReflGainSaved
 * 10012124 -> float RayHeightPrev
 * 10012110 -> float RayAngle0
 * 1001210c -> float LastHeightError
 * 10012108 -> float RayAngle
 * 10012104 -> float RayHeight
 * 10012100 -> float PhaseAccumRad
 * 100120fc -> float LastRayAngleBeforeRefl
 * 100120f8 -> float NextRayHeight
 * 100120f4 -> float SlantSegLen
 * 100120f0 -> float SegSlope
 * 100120ec -> float AlongSegToIntersect
 * 100120e8 -> float HeightAtIntersect
 * 100120e4 -> float SegAngle
 * 100120e0 -> float AngleAdjust
 * 100120dc -> bool UnusedWasAboveTerrain
 * 100120d8 -> float SlopeAtTarget
 * 100120d4 -> float PhaseToRDEdgeRad
 * 100120d0 -> float DirectSlantToRDPoint
 * 100120cc -> float TotalSlantWaves
 * 100120c8 -> float HtRayOut
 * 100120c4 -> float AngleOutRad_RD
 * 100120c0 -> float FinalPhaseGO
 * 100120d0 -> float UnusedSlantToIptIfDirect
 * 100121e8 -> float Slpe2
 * 100121ec -> float Slpe1
 * 10012120 -> float RayHeightPred
 * 10012050 -> int UnusedScanStepIdx
 * 100120b4 -> int SmoothIdx
 * 100120b8 -> int AngleIdx_1_180
 * 100120bc -> int AngleIdx_0_180
 * 10012114 -> int IterCount
 * 10012118 -> int AdjustSign
 * 1001211c -> int CoarseAdjustMode
 * 10012158 -> int NDiffPoints_i4
 * 100121e4 -> int IptDbg
 * 10012224 -> int SweepStepIdx
 * 10012234 -> int InitAngleIdx
 * 1001223c -> short NSmoothedPts_i2

## subroutine REFL (args)

 * a1 -> short IptStart
 * a2 -> short IptEnd
 * a3 -> float RayAngle0
 * a4 -> float RayHeight0
 * a5 -> float FinalPhase
 * a6 -> float ReflAmp
 * a7 -> float PhaseAfterRefl
 * a8 -> float RayHeight
 * a9 -> float RayAngle
 * a10 -> float TotSlantFt
 * a11 -> bool MadeItOut
 * a12 -> bool MadeHit

## subroutine REFL (locals)

 * 10018780 -> int Ipt
 * 10018778 -> float SegSlope
 * 10018774 -> float AlongSegToIntersect
 * 1001877c -> float SlantSegLen
 * 10018770 -> float ReflectPointDistFt
 * 1001876c -> float ReflectPointHeightFt
 * 10018768 -> float SegmentAngleRad
 * 10018764 -> float PhaseIn
 * 10018760 -> float FresnelAngle
 * 10018784 -> float RayHeightCurr

## subroutine DIFFDIFF (args)

 * a1 -> int NPoints
 * a2 -> int NDiffPoints
 * a3 -> int NElements
 * a4 -> int DebugEnable
 * a5 -> int DebugMode
 * a6 -> float DebugExitAngle
 * a7 -> short AntPhase(0:3)
 * a8 -> complex E_diffAccum(0:181)

## subroutine DIFFDIFF (locals)

 * 10011ea0 -> int ElemIdx
 * 10011e9c -> int EdgeIdx1
 * 10011e98 -> int EdgeIdx2
 * 10011e94 -> float Edge12Angle
 * 10011eb0 -> short Edge1_i2
 * 10011eac -> short Edge2_i2
 * 10011e8c -> float ReflPhaseSeed
 * 10011e88 -> float ReflAmpTrace
 * 10011e84 -> float UnusedReflPhase1
 * 10011e90 -> float RayHeightOut2
 * 10011e80 -> float UnusedAngleOut1
 * 10011e7c -> float SlantDist12_ft
 * 10011e78 -> bool MadeItOut
 * 10011e74 -> bool MadeHit
 * 10011e70 -> float ElemGain
 * 10011e6c -> float Slpe1_edge1
 * 10011e68 -> float Slpe2_edge1
 * 10011e64 -> float AInclA
 * 10011e60 -> float PhiP
 * 10011e5c -> float PHR
 * 10011e58 -> int NSteps1
 * 10011e54 -> float E1PhaseLengthFt
 * 10011e50 -> float L1_waves
 * 10011e4c -> float UTD_OutMag
 * 10011e48 -> float UTD_OutPhase
 * 10011e44 -> float AmpAfterE1
 * 10011e40 -> float PhaseAfterE1
 * 10011e3c -> float Slpe1_edge2
 * 10011e38 -> float Slpe2_edge2
 * 10011e34 -> float PHRStepNeg0p25
 * 10011e30 -> int StepIdx2
 * 10011e28 -> float L12_waves
 * 10011e24 -> float PhaseAtE2
 * 10011e20 -> float AmpAtE2
 * 10011e1c -> float PHRF2
 * 10011e18 -> float HG_at_E2
 * 10011ea8 -> short E2_i2
 * 10011ea4 -> short NPoints_i2
 * 10011e14 -> float ReflPhase2
 * 10011e10 -> float AngleOut2
 * 10011e0c -> float UnusedTotSlant2
 * 10011e08 -> float OutputField2
 * 10011e04 -> float AngleIdx_f2
 * 10011e00 -> int AngleIdx2
 * 10011dfc -> float FinalPhase2

## subroutine YUTD (args)

 * a1 -> float FREQ_MHZ
 * a2 -> float L_waves
 * a3 -> float PhiP
 * a4 -> float Incl
 * a5 -> float PHR
 * a6 -> float OutMag
 * a7 -> float OutPhase

## subroutine YUTD (locals)

 * 10011ef0 -> complex UTD_terms4(1:4)
 * 10011ed8 -> complex UTD_sum
 * 10011eec -> float LambdaNormFt
 * 10011ee8 -> float n_wedge
 * 10011ee4 -> float SinBeta0
 * 10011ee0 -> float L_param

## subroutine WD (args)

 * a1 -> complex UTD_terms4(1:4)
 * a2 -> float L_waves
 * a3 -> float PHR
 * a4 -> float PhiP
 * a5 -> float SinBeta0
 * a6 -> float n_wedge

## subroutine WD (locals)

 * 10011f50 -> complex WD_terms4(1:4)
 * 10011f10 -> complex WD_scale
 * 10011f18 -> complex WD_const
 * 10011f50 -> float INV_TWO_PI
 * 10011f4c -> float MIN_N_MARGIN
 * 10011f48 -> float TWO_PI_L
 * 10011f44 -> float INV_n
 * 10011f40 -> float psi_work
 * 10011f3c -> float parity
 * 10011f38 -> int term_idx
 * 10011f30 -> int N_int
 * 10011f34 -> float frac
 * 10011f2c -> float delta
 * 10011f28 -> float a_pm
 * 10011f24 -> float X_arg
 * 10011f20 -> float psi_scaled

## function FFCT (args)

 * a1 -> complex FFCT
 * a2 -> float X

## function FFCT (locals)

 * 10011f7c -> float Xabs
 * 1001155c -> float TAB_X_BREAKS(1:8)
 * 10011518 -> complex TAB_Y_LOW(1:8)
 * 100114d8 -> complex TAB_Y_HIGH(1:8)
 * 10011f78 -> int idx

## function ATN4 (args)

 * a1 -> float X
 * a2 -> float Y

## subroutine FRESNEL (args)

 * a1 -> float FresnelAngle
 * a2 -> float AmpIn
 * a3 -> float PhaseIn
 * a4 -> float AmpOut
 * a5 -> float PhaseOut

## subroutine FRESNEL (locals)

 * 10011fb8 -> float eps_minus_cos2
 * 10011fb4 -> float eps_imag_term
 * 10011fb0 -> float sqrt_eps_mag
 * 10011fac -> float phi_over2
 * 10011fa8 -> float num_real
 * 10011fa4 -> float num_imag
 * 10011fa0 -> float num_abs
 * 10011f9c -> float num_arg
 * 10011f98 -> float den_real
 * 10011f94 -> float den_imag
 * 10011f90 -> float den_abs
 * 10011f8c -> float den_arg
 * 10011f88 -> float Gamma_mag
 * 10011f84 -> float Gamma_arg

## subroutine ANGIN (args)

 * a1 -> float Slpe1
 * a2 -> float Slpe2
 * a3 -> float Incidence
 * a4 -> float Incl
 * a5 -> float PhiP
 * a6 -> float PHR
 * a7 -> int NSteps

## subroutine ANGIN (locals)

 * 10011fbc -> float PHR_start

## subroutine ANGHORIZ (args)

 * a1 -> float Slpe
 * a2 -> float LocalPHR
 * a3 -> float PHRF

## subroutine DRD (args)

 * a1 -> int NPoints
 * a2 -> int NDiffPoints
 * a3 -> int NElements
 * a4 -> int DebugEnable
 * a5 -> int DebugMode
 * a6 -> float DebugExitAngle
 * a7 -> short AntPhase(0:3)
 * a8 -> complex E_diffAccum(0:181)

## subroutine DRD (locals)

 * 10012080 -> int ElemIdx
 * 10012078 -> int EdgeIdx1
 * 10012074 -> int EdgeIdx2
 * 10012070 -> float Edge12Angle
 * 1001206c -> float HtRay_curr
 * 10012068 -> float Slpe1_e1
 * 10012064 -> float Slpe2_e1
 * 10012060 -> float UnusedStartScanAngle
 * 1001205c -> int NStepsScan
 * 10012058 -> float AngleStep
 * 10012054 -> float ScanAngle
 * 100120a8 -> short e1_i2
 * 100120a4 -> short e2_i2
 * 1001204c -> float ReflPhaseIn
 * 10012048 -> float ReflAmp
 * 10012044 -> float ReflPhase
 * 10012040 -> float AngleOut
 * 1001203c -> float SlantDist_e1e2_ft
 * 10012038 -> bool MadeItOut
 * 10012034 -> bool MadeHit
 * 10012030 -> float HtRay_prev
 * 1001202c -> int IterCountFine
 * 10012028 -> int IterIdxFine
 * 10012098 -> short e1_i2_fine
 * 10012094 -> short e2_i2_fine
 * 10012024 -> float DeltaHtRay
 * 10012020 -> int MicroIterIdx
 * 10012090 -> short e1_i2_micro
 * 1001208c -> short e2_i2_micro
 * 1001207c -> bool FoundDRDPath
 * 1001201c -> float ElemGain
 * 10012018 -> float PhaseToE1Rad
 * 10012014 -> float L1_waves
 * 10012010 -> float AInclA
 * 1001200c -> float PhiP
 * 10012008 -> float PHR
 * 10012004 -> int NSteps2
 * 10012000 -> float UTD_OutMag
 * 10011ffc -> float UTD_OutPhase
 * 10011ff8 -> float AmpAfterE1
 * 10011ff4 -> float PhaseAfterE1
 * 10011ff0 -> float Slpe1_e2
 * 10011fec -> float Slpe2_e2
 * 10011fe8 -> float L2Residual_waves
 * 10011fe4 -> int StepIdx2
 * 10011fe0 -> float AmpAtE2
 * 10011fdc -> float UnusedPhaseAtE2
 * 10011fd8 -> float UnusedDRDZero
 * 10011fd4 -> float PhaseBeforeFinalRefl
 * 10011fd0 -> float PHRF2
 * 10011fcc -> float HG_at_E2
 * 10012088 -> short e2_i2_final
 * 10012084 -> short NPoints_i2
 * 10011fc8 -> float ReflPhaseFinal
 * 10011fc4 -> float AngleIdx_f
 * 10011fc0 -> int AngleIdx
 * 1001206c -> float UnusedHtRayFinal
 * 10012044 -> float UnusedFinalPhase

## labels

 * 100040b5 -> Loop_DRD_ReflectionScan
 * 10008ddc -> Loop_ElemScan
 * 1000a6df -> Loop_LaunchAngleScan
