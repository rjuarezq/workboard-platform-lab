CREATE ROLE workboard_migrator
  LOGIN
  PASSWORD :'migrator_password'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOINHERIT;

CREATE ROLE workboard_app
  LOGIN
  PASSWORD :'app_password'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOINHERIT;

ALTER DATABASE :"database_name" OWNER TO workboard_migrator;
ALTER SCHEMA public OWNER TO workboard_migrator;

REVOKE ALL ON DATABASE :"database_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database_name" TO workboard_migrator;
GRANT CONNECT ON DATABASE :"database_name" TO workboard_app;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO workboard_app;

ALTER DEFAULT PRIVILEGES FOR ROLE workboard_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO workboard_app;

ALTER DEFAULT PRIVILEGES FOR ROLE workboard_migrator IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO workboard_app;