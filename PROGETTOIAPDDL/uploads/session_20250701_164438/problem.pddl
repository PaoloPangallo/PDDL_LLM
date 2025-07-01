(:domain quest)
   (:objects
      (hero hero)
      (tower-of-varnak tower-of-varnak)
      (sword-of-fire sword-of-fire)
      (ice-dragon ice-dragon)
      (village village)
   )
   (:init
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon))
   (:goal (and (at hero tower-of-varnak) (defeated ice-dragon)))