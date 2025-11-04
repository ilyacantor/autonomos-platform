
{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.libxcrypt
    pkgs.libyaml
    pkgs.openssl
    pkgs.redis
    pkgs.imagemagick
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.postgresql_16
  ];
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      pkgs.libxcrypt
    ];
    PYTHONBIN = "${pkgs.python311}/bin/python3.11";
    LANG = "en_US.UTF-8";
    STDERREDIRECT = "${pkgs.python311}/bin/python3.11";
    MYPYPATH = "${pkgs.python311Packages.pip}/${pkgs.python311.sitePackages}";
  };
}
