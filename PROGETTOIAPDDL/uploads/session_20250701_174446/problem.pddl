(:domain hero-quest)
   (:objects hero tower-of-varnak sword-of-fire ice-dragon village)
   (:init
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon)
      (at-location tower-of-varnak))
   (:goal (and (at hero tower-of-varnak) (defeated ice-dragon)))