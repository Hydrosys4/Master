drop table if exists sensordata;
create table sensordata (
id integer primary key autoincrement,
readtime text,
temp1 Single,
temp2 Single,
temp3 Single,
temp4 Single,
ph1 Single,
ph2 Single,
ec1 Single,
ec2 Single,
light1 Single,
light2 Single,
humid1 Single,
humid2 Single
);
