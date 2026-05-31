{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-26.05";
    systems.url = "github:nix-systems/default";
  };

  outputs = {nixpkgs, systems, ...}: let
    forEachSystem = nixpkgs.lib.genAttrs (import systems);
  in {
    packages = forEachSystem (system: rec {
      openhfta = nixpkgs.legacyPackages.${system}.callPackage ./default.nix {};
      default = openhfta;

      openhfta-with-difftests = openhfta.override { withDiffTests = true; };
    });
    overlays.default = final: _prev: {
      openhfta = final.callPackage ./default.nix {};
    };
  };
}
