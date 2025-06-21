(define (domain traveling-world)
       (:requirements :strips)
       (:types location person)
       (:predicates
         (at ?p - person ?l - location)
         (city ?c - location)
         (capital ?c - location)
         (traveling-to ?p - person ?l - location)
       )

       (:action move
         :parameters (?p - person ?from - location ?to - location)
         :precondition (and (at ?p ?from) (not (traveling-to ?p ?to)))
         :effect (and (not (at ?p ?from)) (at ?p ?to) (traveling-to ?p ?to))
       )

       (:action rest
         :parameters (?p - person)
         :precondition (and (at ?p ?location) (city ?location))
         :effect (not (traveling-to ?p ?location1)))
       (:action travel
         :parameters (?p - person ?from - location ?to - location)
         :precondition (and (at ?p ?from) (city ?from) (capital ?to))
         :effect (and (not (at ?p ?from)) (at ?p ?to) (traveling-to ?p ?to)))