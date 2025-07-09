(define (domain example)
  (:requirements :strips :conditional-effects :adl)
  (:predicates
    (at ?x - object ?y - location)
    (free ?x - object)
    (has ?x - object ?y - container)
  )
  (:action move
    (:parameters (?obj - object ?from - location ?to - location))
    (:precondition (and (at ?obj ?from) (free ?obj)))
    (:effect (and (at ?obj ?to) (not (at ?obj ?from)) (free ?obj)))
  )
  (:action pickup
    (:parameters (?obj - object))
    (:precondition (and (at ?obj ?loc) (free ?obj)))
    (:effect (and (not (at ?obj ?loc)) (free ?obj)))
  )
  (:action drop
    (:parameters (?obj - object ?loc - location))
    (:precondition (and (at ?obj ?loc) (not (free ?obj))))
    (:effect (and (at ?obj ?loc) (free ?obj)))
  ))