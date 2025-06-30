(define (domain simple_puzzle)
          (:requirements :equality :strips)
          (:types agent location object goal)
          (:predicates
           (at ?x ?loc)
           (on-ground ?o ?loc)
           (carrying ?a ?o)
           (has_goal ?a ?g))

          (:action move
           :parameters (?a ?from ?to)
           :precondition (and (at ?a ?from))
           :effect (and (not (at ?a ?from)) (at ?a ?to)))

          (:action pick_up
           :parameters (?a ?o)
           :precondition (and (on-ground ?o ?loc) (at ?a ?loc) (not (carrying ?a ?o)))
           :effect (and (carrying ?a ?o) (not (on-ground ?o ?loc))))

          (:action put_down
           :parameters (?a ?o)
           :precondition (and (carrying ?a ?o))
           :effect (and (on-ground ?o ?loc) (not (carrying ?a ?o))))