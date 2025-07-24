(define (domain ElvenRealm)
  (:requirements :strips :typing)
  (:types agent location item monster)
  (:predicates
    (at        ?a  - agent    ?l - location)
    (item_at   ?i  - item     ?l - location)
    (has       ?a  - agent    ?i - item)
    (can_move  ?from - location  ?to - location)
    (is_dangerous ?l - location)
    (defeated  ?m  - monster)
  )
  (:action TravelTo
    :parameters (?a    - agent ?from - location ?to - location)
    :precondition (and (at ?a ?from)
                       (can_move ?from ?to))
    :effect      (and (at ?a ?to)
                       (not (at ?a ?from)))
  )
  (:action CollectItem
    :parameters (?a    - agent ?i    - item     ?l - location)
    :precondition (and (at ?a ?l)
                       (item_at ?i ?l))
    :effect      (and (has ?a ?i)
                       (not (item_at ?i ?l)))
  )
  (:action DefeatMonster
    :parameters (?a    - agent
                 ?m    - monster
                 ?l    - location
                 ?i    - item)
    :precondition (and (at ?a ?l)
                       (is_dangerous ?l)
                       (has ?a ?i))
    :effect      (and (defeated ?m)
                       (not (is_dangerous ?l)))
  )
)