(define (domain dragon-and-sword)
     (:requirements :equality :quantifiers)
     (:types agent location object dragon sword)
     (:predicates
      (at ?a ?loc)
      (on-ground ?o ?loc)
      (carrying ?h ?o)
      (sleeping ?d)
      (alive ?d)
      (defeated ?d))
     (:action pickup
      :parameters (?h ?o)
      :precondition (and (at ?h ?loc1) (on-ground ?o ?loc2) (not (carrying ?h ?o)))
      :effect (and (not (on-ground ?o ?loc2)) (carrying ?h ?o) (not (at ?h ?loc1))))
     (:action putdown
      :parameters (?h ?o)
      :precondition (and (carrying ?h ?o))
      :effect (and (at ?h ?loc) (on-ground ?o ?loc) (not (carrying ?h ?o))))
     (:action move
      :parameters (?a ?toLoc)
      :precondition (at ?a ?fromLoc)
      :effect (and (not (at ?a ?fromLoc)) (at ?a ?toLoc)))
     (:action wake-dragon
      :parameters (?d)
      :precondition (at ?d 'tower-of-varnak)
      :effect (not (sleeping ?d)))
     (:action defeat-dragon
      :parameters (?h)
      :precondition (and (carrying ?h 'sword-of-fire) (alive ?d) (at ?h 'tower-of-varnak))
      :effect (and (defeated ?d)))
   )