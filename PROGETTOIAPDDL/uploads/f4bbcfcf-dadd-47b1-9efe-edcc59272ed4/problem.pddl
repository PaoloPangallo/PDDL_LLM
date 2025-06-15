(define (problem swords-and-dragons-problem)
     (domain swords-and-dragons)
     :objects (hero dragon1 sword1 sword2)
     :init
       (and (at hero village) (hidden sword cave) (asleep dragon1))
     :goal
       (and (has hero sword1) (defeated dragon1))
   )