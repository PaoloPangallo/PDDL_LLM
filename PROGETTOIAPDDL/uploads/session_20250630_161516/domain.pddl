(define (domain quest-adventure)
     (:requirements :equality :typed :static :quantifiers none)
     (:types agent artifact location)
     (:predicates
      (at ?a ?l)
      (has-item ?a ?i)
      (in-location ?i ?l))
     (:action take-item
              (:parameters ?a ?i)
              (:precondition (and (at ?a ?l) (in-location ?i ?l)))
              (:effect (not (in-location ?i ?l)) (and (has-item ?a ?i) (not (at ?i ?l)))) )
     (:action drop-item
              (:parameters ?a ?i)
              (:precondition (and (has-item ?a ?i)))
              (:effect (in-location ?i ?l) (not (has-item ?a ?i)))) )