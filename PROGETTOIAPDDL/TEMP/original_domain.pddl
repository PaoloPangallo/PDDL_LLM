(define (domain dragon-tower)
     (:requirements :equality :typing :fluent :duration)
     (:types agent object dragon fire-dragon sleeping)
     (:predicates
       (at ?a ?loc)
       (on-ground ?o ?l)
       (carrying ?h ?o)
       (sleeping ?d))
     (:action pick-up
              (:parameters ?h ?o)
              (:precondition and (at ?h ?loc) (and (on-ground ?o ?loc) (not (carrying ?h ?o))))
              (:effect (and (not (on-ground ?o ?loc)) (carrying ?h ?o)
                             (not (at ?h ?loc)))))
     (:action put-down
              (:parameters ?h ?o)
              (:precondition and (carrying ?h ?o))
              (:effect (and (on-ground ?o ?loc) (not (carrying ?h ?o))
                             (at ?h ?loc))))
     (:action move-to
              (:parameters ?a ?d)
              (:precondition at ?a ?loc)
              (:effect (and (not (at ?a ?loc)) (at ?a ?d))))
     (:action wake-dragon
              (:parameters ?h)
              (:precondition and (carrying ?h sword-of-fire) (at ?h tower-of-varnak))
              (:effect (not (sleeping ice-dragon))))
   )