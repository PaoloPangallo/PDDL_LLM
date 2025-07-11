(define (domain infiltrate_halcyon)
  (:requirements :strips :typing)
  (:types location object target action)
  (:predicates
    (at ?x - object ?y - location)
    (contains ?x - object ?y - target)
    (has_access ?x - object ?y - location)
    (can_disable ?x - object ?y - location)
    (can_bribe ?x - object ?y - location)
    (can_escape ?x - object ?y - location)
    (secured ?x - object)
  )
  (:action disable_cctv
    :parameters (?hacker - object ?location - location)
    :precondition (and (at ?hacker ?location) (has_access ?hacker ?location) (can_disable ?hacker ?location))
    :effect (and (secured ?hacker)))
  (:action bribe_insider
    :parameters (?hacker - object ?location - location)
    :precondition (and (at ?hacker ?location) (has_access ?hacker ?location) (can_bribe ?hacker ?location))
    :effect (and (secured ?hacker)))
  (:action escape_helicopter
    :parameters (?hacker - object ?location - location)
    :precondition (and (at ?hacker ?location) (has_access ?hacker ?location) (can_escape ?hacker ?location))
    :effect (and (secured ?hacker)))
  (:action escape_metro
    :parameters (?hacker - object ?location - location)
    :precondition (and (at ?hacker ?location) (has_access ?hacker ?location) (can_escape ?hacker ?location))
    :effect (and (secured ?hacker)))
)