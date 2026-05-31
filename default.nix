{
  lib,
  stdenv,
  gfortran,
  python3,

  withDiffTests ? false,
  requireFile,
  pkgsCross,
  wine,
  writableTmpDirAsHomeHook,
}: stdenv.mkDerivation {
  pname = "openhfta";
  version = "main";
  meta.mainProgram = "hfta";
  src = ./.;

  nativeBuildInputs = [gfortran];
  buildInputs = [
    (python3.withPackages (p: [
      p.numpy
      p.matplotlib
    ]))
  ];
  doCheck = true;
  makeFlags = ["PREFIX=$(out)"];

  # If differential tests are enabled, set them up
  preCheck = let
    rev = "e6f70f26810dc0acef2621587369697959f74a58";
    requireDll = name: hash: requireFile {
      inherit name hash;
      url = "https://github.com/RioDXGroup/openhfta-private-testdata/raw/${rev}/${name}";
    };
    ytwcore = requireDll "YTWCore.dll" "sha256-315GWJm8NJKL2QSY1fmy+DR5BPzdZuPAVPIEzEGhyEI=";
    dforrt = requireDll "DFORRT.DLL" "sha256-ah0y4i/jCVfZB71+cs4UMTB3omTeHOJltxux7NpYH3c=";
  in lib.optionalString withDiffTests ''
    ln -s ${ytwcore} test/YTWCore.dll
    ln -s ${dforrt} test/DFORRT.DLL
  '';
  nativeCheckInputs = lib.optionals withDiffTests [
    wine
    pkgsCross.mingw32.buildPackages.gfortran
    writableTmpDirAsHomeHook 
  ];
  checkFlags =  lib.optionals withDiffTests [
    "WINEPATH='${lib.concatStringsSep ";" [
      "${pkgsCross.mingw32.buildPackages.gfortran.cc.lib}/lib"
      "${pkgsCross.mingw32.threads.package}/bin"
    ]}'"
  ];
}
