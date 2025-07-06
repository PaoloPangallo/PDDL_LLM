(define (problem varnack-problem)
  (:domain varnack-problem)
  (:objects astronaut - agent
            crater - location
            base - location
            sample - object
            rover - vehicle)
  (:init 
    (at astronaut base)
    (at rover base)
    (at sample crater))
  (:goal 
    (and (at astronaut base)
         (has astronaut sample))))