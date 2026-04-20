-- Run in Workbench if you already executed an older schema.sql (e.g. had demo@duracapital.com).
-- Replaces all users with the owner account below. Does not delete instruments or uploads.

USE dura_capital;

DELETE FROM users;

INSERT INTO users (email, password_hash) VALUES (
  'makanakakanyai@gmail.com',
  'scrypt:32768:8:1$hbkr0iW6TKT5cDac$d78aa0e5dcf3c10bf2dbcde4b8825af5b9c8cc1c865cc4dd80b127514c5d3ea8911d98086e6029f9b94178921e8787e8dc0f7c3185f2d5b3221c4e78c55992b4'
);
