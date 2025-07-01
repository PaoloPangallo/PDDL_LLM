(:domain tower-quest)
   (:objects hero sword-of-fire ice-dragon village tower-of-varnak)
   (:init
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon))
   (:goal (and (at hero tower-of-varnak) (not (sleeping ice-dragon))))