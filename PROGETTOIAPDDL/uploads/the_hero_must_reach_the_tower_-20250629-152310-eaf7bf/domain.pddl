(define (domain simple_maze)
    (:requirements :strips)
    (:types agent location)
    (:predicates
      (at ?a - agent ?l - location)
      (left-of ?l1 - location ?l2 - location)
      (adjacent ?l1 - location ?l2 - location)
      (on-table ?o - object)
      (clear ?l - location)
    )

    (:action move-north
      :parameters (?a - agent ?l - location)
      :precondition (and (at ?a ?l) (clear ?l) (not (on-table ?a)))
      :effect (and (not (at ?a ?l)) (at ?a (if (left-of ?l 'start) 'goal (find-next-north ?l))) (clear ?l))
    )

    (:action move-south
      :parameters (?a - agent ?l - location)
      :precondition (and (at ?a ?l) (clear ?l) (not (on-table ?a)))
      :effect (and (not (at ?a ?l)) (at ?a (if (left-of (find-next-south ?l) 'end) '(find-next-south ?l) 'end)) (clear ?l))
    )

    (:action move-east
      :parameters (?a - agent ?l - location)
      :precondition (and (at ?a ?l) (clear ?l) (not (on-table ?a)))
      :effect (and (not (at ?a ?l)) (at ?a (if (left-of ?l 'start) (find-next-east ?l) 'end)) (clear ?l))
    )

    (:action move-west
      :parameters (?a - agent ?l - location)
      :precondition (and (at ?a ?l) (clear ?l) (not (on-table ?a)))
      :effect (and (not (at ?a ?l)) (at ?a (if (left-of (find-next-west ?l) 'start) 'goal (find-next-west ?l))) (clear ?l))
    )

    (:action pick-up
      :parameters (?a - agent ?o - object)
      :precondition (and (on-table ?o) (at ?a (find-position ?o)))
      :effect (and (not (on-table ?o)) (held ?a ?o))
    )

    (:action put-down
      :parameters (?a - agent ?o - object)
      :precondition (held ?a ?o)
      :effect (and (on-table ?o) (not (held ?a ?o)))
    )
  )