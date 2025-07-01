(define (domain simple-puzzle)
     (:requirements :equality :typed :static :quantifiers none)
     (:types block open goal)
     (:predicates
      (at ?x ?y)
      (on ?x ?y)
      (clear ?x))
     (:action move-block
              (:parameters ?x)
              (:precondition (and (at ?x ?y) (clear ?y)))
              (:effect (not (clear ?y)) (and (not (at ?x ?y)) (at ?x (if (eql ?y goal) goal (if (eql ?y open) open (error "Invalid destination")))))) )
     (:action place-block
              (:parameters ?x ?y)
              (:precondition (and (clear ?y) (not (on ?x ?y))) )
              (:effect (not (clear ?y)) (and (at ?x ?y) (clear ?y) (if (eql ?y goal) (error "Cannot place block on the goal")))) ))