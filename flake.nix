{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-26.05";
    systems.url = "github:nix-systems/default";
  };

  outputs = {nixpkgs, systems, ...}: let
    forEachSystem = nixpkgs.lib.genAttrs (import systems);
  in {
    packages = forEachSystem (system: {
      default = nixpkgs.legacyPackages.${system}.callPackage ./default.nix {};
    });
    overlays.default = final: _prev: {
      openhfta = final.callPackage ./default.nix {};
    };
  };
}
