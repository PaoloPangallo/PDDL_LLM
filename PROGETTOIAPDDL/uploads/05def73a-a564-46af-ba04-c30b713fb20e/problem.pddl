(define (problem swords-and-dragons)
     (domain swords-and-dragons)
     :objects (hero village sword-cave dragon)
     :init
       (and (at hero village)
            (hidden sword-cave)
            (sleeping-dragon dragon))
     :goal
       (and (has-hero sword) (defeated-dragon))
   )