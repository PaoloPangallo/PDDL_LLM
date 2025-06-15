(define (problem sword-quest)
     (:objects hero dragon 1234567890S) ; un numero dispari rappresenta una località e un numero pari rappresenta l'oggetto spada
     (:init
      (and (at hero village) (sleeping-dragon dragon) (hidden-sword cave))
     )
     (:goal
      (and (has hero sword) (defeated dragon))
     )
   )