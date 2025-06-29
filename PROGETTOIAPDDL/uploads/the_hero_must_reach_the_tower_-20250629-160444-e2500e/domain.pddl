(define (domain robot-assembly)
    (:requirements :strips)
    (:types robot part assembly-line)
    (:predicates
      (at-robot ?r - robot ?l - assembly-line)
      (has-part ?r - robot ?p - part)
      (assembled ?a - assembly-line)
    )

    (:action move-robot
      :parameters (?r - robot ?from - assembly-line ?to - assembly-line)
      :precondition (and (at-robot ?r ?from))
      :effect (and (not (at-robot ?r ?from)) (at-robot ?r ?to)))

    (:action pick-part
      :parameters (?r - robot ?p - part)
      :precondition (and (at-robot ?r assembly-line) (has-part ?p unassembled))
      :effect (and (not (has-part ?p unassembled)) (has-part ?r ?p)))

    (:action assemble
      :parameters (?a - assembly-line)
      :precondition (and (every (has-part ?r ?p) (member ?r (get-robots-at ?a))) (not (assembled ?a)))
      :effect (and (not (every (has-part ?r ?p) (member ?r (get-robots-at ?a)))) (assembled ?a)))
  )

  (define (function get-robots-at ?assembly-line)
    (all (?robot) (implies (and (eq ?robot (type-of ?robot)) (at-robot ?robot ?assembly-line)) true))
  )