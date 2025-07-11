(define (domain hero-journey)
  (:requirements :strips :typing :conditional-effects)
  (:types agent location object monster)
  (:constants
    village forest dark_cave tower - location
    sword_of_fire - object
    ice_dragon bandit goblin - monster
  )

  (:predicates
    (at            ?h - agent    ?l - location)
    (on_ground     ?o - object   ?l - location)
    (sleeping      ?d - monster)
    (explored      ?l - location)
    (rested        ?h - agent)
    (visited-forest)
    (visited-cave)
    (defeated      ?m - monster)
  )

  (:action move
    :parameters (?h - agent ?from - location ?to - location)
    :precondition (at ?h ?from)
    :effect (and
      (not (at ?h ?from))
      (at     ?h ?to)
    )
  )

  (:action carry-and-move
    :parameters (?h - agent ?o - object ?from - location ?to - location)
    :precondition (and
      (at        ?h ?from)
      (on_ground ?o ?from)
    )
    :effect (and
      (not (at        ?h ?from))
      (at     ?h ?to)
      (not (on_ground ?o ?from))
      (on_ground ?o ?to)
    )
  )

  (:action explore
    :parameters (?h - agent ?l - location)
    :precondition (at ?h ?l)
    :effect (and
      (explored ?l)
      (when (and (at ?h forest)    (explored forest))    (visited-forest))
      (when (and (at ?h dark_cave) (explored dark_cave)) (visited-cave))
    )
  )

  (:action rest
    :parameters (?h - agent ?l - location)
    :precondition (at ?h ?l)
    :effect (rested ?h)
  )

  (:action defeat-forest
    :parameters (?h - agent ?b - monster ?l - location)
    :precondition (and
      (at            ?h ?l)
      (visited-forest)
      (at            ?b forest)
    )
    :effect (defeated ?b)
  )

  (:action defeat-cave
    :parameters (?h - agent ?g - monster ?l - location)
    :precondition (and
      (at          ?h ?l)
      (visited-cave)
      (at          ?g dark_cave)
    )
    :effect (defeated ?g)
  )

  (:action defeat-dragon-via-forest
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and
      (at                ?h ?l)
      (on_ground         sword_of_fire ?l)
      (sleeping          ?d)
      (visited-forest)
    )
    :effect (and
      (defeated ?d)
      (not (sleeping ?d))
    )
  )

  (:action defeat-dragon-via-cave
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and
      (at                ?h ?l)
      (on_ground         sword_of_fire ?l)
      (sleeping          ?d)
      (visited-cave)
    )
    :effect (and
      (defeated ?d)
      (not (sleeping ?d))
    )
  )
  (:action defeat-dragon
 :parameters (?h - agent ?d - monster ?l - location)
 :precondition (and
   (at ?h ?l)
   (explored ?l)
   (or
     (visited-forest)
     (visited-cave)
   )
 )
 :effect (and
   (defeated ?d)
   (not (sleeping ?d))
 )
)
)
