(define (domain my_domain)
   (:requirements :equality :quantifiers :action-cost)
   (:predicates
      (at ?x - Location)
      (has_ball - Agent))
   (:action pickup
      (:parameters (?x - Location) (?y - Agent))
      (:precondition (and (at ?x ?y) (not (has_ball ?y))) )
      (:effect (and (not (at ?x ?y)) (at ?x unoccupied) (has_ball ?y))))
   (:action putdown
      (:parameters (?x - Location) (?y - Agent))
      (:precondition (and (at ?x ?y) (has_ball ?y)))
      (:effect (and (not (at ?x ?y)) (at unoccupied ?x) (not (has_ball ?y))))
)