(:domain quest-tower-of-varnak
    (:objects hero village tower-of-varnak sword-of-fire ice-dragon)
    (:init
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon))
    (:goal (and (at hero tower-of-varnak) (fight hero ice-dragon))))