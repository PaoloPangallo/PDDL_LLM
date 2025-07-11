(define (domain xr17-navigation)
  (:requirements :strips :typing)
  (:types location route method action)
  (:predicates
    (at ?x - location)
    (reachable ?x - location)
    (has-route ?x - location ?y - location)
    (use-method ?x - method)
    (contact-restored)
  )
  (:action navigate
    :parameters (?current - location ?next - route ?method - method)
    :precondition (and (at ?current) (reachable ?next) (has-route ?current ?next) (use-method ?method))
    :effect (and (not (at ?current)) (at ?next) (use-method ?method) (contact-restored)))
  (:action recharge
    :parameters (?loc - location)
    :precondition (at ?loc)
    :effect (reachable ?loc))
)