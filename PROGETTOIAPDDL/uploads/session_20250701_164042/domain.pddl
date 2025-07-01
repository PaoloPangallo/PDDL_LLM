(:domain hero-adventure)

   (:requirements :strips :equality :typing)
   (:types agent location monster object)
   (:predicates
      (at ?agent ?location)
      (on-ground ?object ?location)
      (carrying ?agent ?object)
      (sleeping ?monster)
      (defeated ?monster))

   (:action move
      :parameters (?agent ?destination)
      :precondition (and (at ?agent ?source) (not (= ?source ?destination)))
      :effect (and (not (at ?agent ?source)) (at ?agent ?destination)))

   (:action pickup
      :parameters (?agent ?object)
      :precondition (and (on-ground ?object ?location) (at ?agent ?location))
      :effect (and (not (on-ground ?object ?location)) (carrying ?agent ?object)))

   (:action putdown
      :parameters (?agent ?object)
      :precondition (and (carrying ?agent ?object) (at ?agent ?location))
      :effect (and (on-ground ?object ?location) (not (carrying ?agent ?object))))

   (:action fight
      :parameters (?agent ?monster)
      :precondition (and (at ?agent ?location) (carrying sword-of-fire) (sleeping ?monster))
      :effect (and (awake ?monster) (defeated ?monster)))