begin_version
3
end_version
begin_metric
0
end_metric
3
begin_variable
var0
-1
2
Atom at(hero, tower_of_varnak)
Atom at(hero, village)
end_variable
begin_variable
var1
-1
3
Atom carrying(hero, sword_of_fire)
Atom on-ground(sword_of_fire, tower_of_varnak)
Atom on-ground(sword_of_fire, village)
end_variable
begin_variable
var2
-1
2
Atom defeated(ice_dragon)
NegatedAtom defeated(ice_dragon)
end_variable
0
begin_state
1
1
1
end_state
begin_goal
3
0 0
1 0
2 0
end_goal
8
begin_operator
defeat-monster hero ice_dragon sword_of_fire tower_of_varnak
2
0 0
1 0
1
0 2 -1 0
1
end_operator
begin_operator
defeat-monster hero ice_dragon sword_of_fire village
2
0 1
1 0
1
0 2 -1 0
1
end_operator
begin_operator
drop-object hero sword_of_fire tower_of_varnak
1
0 0
1
0 1 0 1
1
end_operator
begin_operator
drop-object hero sword_of_fire village
1
0 1
1
0 1 0 2
1
end_operator
begin_operator
move-agent hero tower_of_varnak village
0
1
0 0 0 1
1
end_operator
begin_operator
move-agent hero village tower_of_varnak
0
1
0 0 1 0
1
end_operator
begin_operator
pick-object hero sword_of_fire tower_of_varnak
1
0 0
1
0 1 1 0
1
end_operator
begin_operator
pick-object hero sword_of_fire village
1
0 1
1
0 1 2 0
1
end_operator
0
