{
  description = "A Python project with dependencies from requirements.txt and build.sh support";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };

        pythonEnv = pkgs.python3.withPackages (
          ps: with ps; [
            watchdog
            python-dotenv
            colorama
            requests
            psutil
            pyinstaller
            selenium
            webdriver-manager
            arabic-reshaper
            python-bidi
            faker

            # Windows-only: pywin32 (won't be included on non-Windows systems)
          ]
        );

        # Shell with Python environment
        devShell = pkgs.mkShell {
          name = "python-env-shell";

          buildInputs = [
            pythonEnv
            pkgs.bash
          ];

          # Environment variables (optional)
          shellHook = ''
            echo "Python environment ready."
            echo "Run ./build.sh to build your project."
          '';
        };
      in
      {
        devShells.default = devShell;
      }
    );
}
