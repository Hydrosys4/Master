drop table if exists nutrients;
create table nutrients (
id integer primary key autoincrement,
name not null,
week integer,
phase not null,
nut1quantity integer,
nut2quantity integer,
nut3quantity integer,
nut4quantity integer,
phminquantity Single,
phmaxquantity Single,
ecminquantity Single,
ecmaxquantity Single
);