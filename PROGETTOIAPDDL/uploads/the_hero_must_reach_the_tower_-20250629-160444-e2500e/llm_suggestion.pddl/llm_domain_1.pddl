(define (domain my_domain)
  (:requirements :equality :quantifiers :actions)

  (:predicates
    (at ?x ?y)       ; Define the predicate 'at' if it's not defined yet.
    (clear ?x)
    (blocked ?x ?y)
    ...
  )

  (:action action_name
    :parameters (?x ?y)
    :precondition (and (at ?x ?y) (not (clear ?x))) ; Check the preconditions.
    :effect (and (not (at ?x ?y)) (clear ?x) (at ?x new_location) (not (blocked ?new_location ?y)))) ; Define the effects correctly.
  ...
)