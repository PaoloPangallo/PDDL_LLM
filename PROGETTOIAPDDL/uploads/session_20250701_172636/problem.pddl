(:domain tower-defense)
   (:objects hero village tower-of-varnak sword-of-fire ice-dragon)
   (:init
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon))
   (:goal (and (at hero tower-of-varnak) (awake ice-dragon) (fight hero ice-dragon)))