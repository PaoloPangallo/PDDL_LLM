(define (problem dragon-kingdom)
     (:domain dragon-and-sword)
     (:objects hero tower-of-varnak sword ice-dragon village)
     (:init
      (and (at hero village) (on-ground sword tower-of-varnak) (sleeping ice-dragon)))
     (:goal (and (defeated ice-dragon) (at hero village)))
   )