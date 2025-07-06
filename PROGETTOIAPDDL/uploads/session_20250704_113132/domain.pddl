(define (domain hero))
(:requirements :strips :typing :negative-preconditions :adl :durative-actions)

(:types hero sword-of-fire tower-of-varnak ice-dragon)

(:predicates (at ?x ?y)
             (carrying ?hero ?sword)
             (sleeping ?ice-dragon)
             (awake ?ice-dragon))

(:action walk-to-tower
   :parameters (?hero - hero ?target - tower-of-varnak)
   :precondition (and (at ?hero ?x) (not (at ?hero ?target)))
   :effect (and (at ?hero ?target) (not (at ?hero ?x))))

(:action collect-sword
   :parameters (?hero - hero ?sword - sword-of-fire)
   :precondition (and (carrying ?hero ?sword) (at ?hero ?tower))
   :effect (and (at ?hero ?tower) (not (carrying ?hero ?sword))))

(:action go-to-sleep
   :parameters (?ice-dragon - ice-dragon)
   :precondition (and (sleeping ?ice-dragon) (at ?ice-dragon ?location))
   :effect (and (not (at ?ice-dragon ?location)) (asleep ?ice-dragon)))

(:action wake-up
   :parameters (?ice-dragon - ice-dragon)
   :precondition (and (asleep ?ice-dragon) (not (awake ?ice-dragon)))
   :effect (and (not (asleep ?ice-dragon)) (awake ?ice-dragon)))

(:action defeat-ice-dragon
   :parameters (?hero - hero ?ice-dragon - ice-dragon)
   :precondition (and (at ?hero ?tower) (carrying ?hero ?sword) (awake ?ice-dragon))
   :effect (and (defeated ?ice-dragon)))