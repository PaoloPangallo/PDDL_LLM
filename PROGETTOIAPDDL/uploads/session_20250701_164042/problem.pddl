(:domain hero-adventure)

   (:objects
      (hero)
      (tower-of-varnak location)
      (sword-of-fire object)
      (ice-dragon monster))

   (:init
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon))

   (:goal
      (and (at hero tower-of-varnak) (defeated ice-dragon)))