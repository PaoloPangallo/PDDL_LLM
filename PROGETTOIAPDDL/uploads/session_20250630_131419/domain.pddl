(define (domain dragon-tower)
     (:requirements :equality :typed :static :quantifiers none)
     (:types agent dragon item location)
     (:predicates
      (at ?a ?l)
      (on-ground ?i ?l)
      (carrying ?a ?i)
      (sleeping ?d)
      (awake ?d))
     (:action take-item
              (:parameters ?a ?i)
              (:precondition (and (at ?a ?l) (on-ground ?i ?l)))
              (:effect (not (on-ground ?i ?l)) (and (holding ?a ?i) (not (at ?i ?l)))) )
     (:action drop-item
              (:parameters ?a ?i)
              (:precondition (and (holding ?a ?i)))
              (:effect (on-ground ?i (location ?a)) (not (holding ?a ?i))) )
     (:action wake-dragon
              (:parameters ?d)
              (:precondition (at ?d tower))
              (:effect (not (sleeping ?d))))
     (:action defeat-dragon
              (:parameters ?h)
              (:precondition (and (carrying ?h sword-of-fire) (awake dragon)))
              (:effect (not (alive ?d)))) )