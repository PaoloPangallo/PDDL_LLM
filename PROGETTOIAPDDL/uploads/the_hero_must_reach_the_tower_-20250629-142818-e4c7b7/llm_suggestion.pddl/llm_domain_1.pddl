(define (domain simple-world)
  (:requirements :equality :typing :quantifiers)
  (:predicates
    (and on ?x - Location
         (not (= ?x nil))
         (All ?y (- Block - Object)
           (implies (on ?y ?x)
                     (or (and (= ?x Table) (clear ?y))
                         (and (= ?x Hand) (held ?y)))))))
  (:action pick-up
    :parameters (?x - Location ?y - Block)
    :precondition (and (on ?y ?z) (clear ?x))
    :effect (and (not (on ?y ?z)) (on ?y ?x) (clear ?z)))
  (:action put-down
    :parameters (?x - Location ?y - Block)
    :precondition (and (on ?x ?y))
    :effect (and (not (on ?x ?y)) (clear ?y) (clear ?x))))