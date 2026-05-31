{stdenv, gfortran, python3}: stdenv.mkDerivation {
  pname = "openhfta";
  version = "main";
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
  meta.mainProgram = "hfta";
}
