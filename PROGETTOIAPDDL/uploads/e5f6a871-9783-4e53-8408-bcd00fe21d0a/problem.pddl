(define (problem la-spada-di-varnak))
   (domain sword-and-dragon)
   (:objects hero sleeping-dragon cave hidden-cave sword)
   (:init
      (at hero village)
      (hidden hidden-cave)
      (sleeping sleeping-dragon)
   )
   (:goal
      (and (has hero sword) (defeated sleeping-dragon))
   )