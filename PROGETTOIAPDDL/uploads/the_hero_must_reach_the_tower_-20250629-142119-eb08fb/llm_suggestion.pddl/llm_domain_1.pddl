(define (domain my-planning)
  (:requirements :equality :qualified :strips :regular :history)
  (:action move
    :parameters (?x ?y)
    :precondition (and (at ?x ?y) (clear ?y))
    :effect (and (at ?x ?y) (not (at ?x ?x)))
  )
)