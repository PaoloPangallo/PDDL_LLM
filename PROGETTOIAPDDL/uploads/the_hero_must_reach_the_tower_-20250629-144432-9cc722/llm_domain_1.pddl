(define (domain my-domain)
  :requires all (action do-something)
  :effects (condition (and (at p1 goal) (at p2 goal)))
  (action do-something
    :parameters (?x - integer)
    :precondition (and (at ?x start))
    :effect (and (at ?x goal))))