{pkgs}: {
  deps = [
    pkgs.python311Full
    pkgs.redis
    pkgs.postgresql_16
  ];
}