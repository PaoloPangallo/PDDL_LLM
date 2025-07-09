(define (domain collect-sample)
  (:requirements :strips :typing)
  (:types rover astronaut sample base location)
  (:predicates (at ?x - object ?y - location)
               (has ?a - agent ?o - object))
  (:action move-rover
    :parameters (?r - rover ?f - from ?t - to)
    :precondition (and (at ?r ?f) (location ?f) (not (at ?r ?t)))
    :effect (and (at ?r ?t) (not (at ?r ?f))))
  (:action collect-sample
    :parameters (?a - astronaut ?s - sample)
    :precondition (and (at ?a base) (at ?s crater))
    :effect (and (has ?a ?s) (at ?s crater)))
  (:action return-to-base
    :parameters (?r - rover ?s - sample)
    :precondition (and (has ?s astronaut) (at ?s crater) (at ?r ?s))
    :effect (and (at ?r base) (not (has ?s astronaut))))
)