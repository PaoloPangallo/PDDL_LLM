(:domain quest_adventure
    (:requirements :equality :quantifiers :typing :time :timed :fluent)
    (:types agent monster location object)
    (:predicates
     (at agent location)
     (on-ground object location)
     (carrying agent object)
     (sleeping monster)
     (awake monster))
    (:action move-to
     :parameters (?a - agent ?l - location)
     :precondition (and (at ?a ?c) (not (= ?c ?l)))
     :effect (when (not (at ?a ?l)) (at ?a ?l) (not (at ?a ?c))))
    (:action take-item
     :parameters (?a - agent ?o - object ?l - location)
     :precondition (and (on-ground ?o ?l) (at ?a ?l))
     :effect (when (not (on-ground ?o ?l)) (on-ground ?o ?a) (not (on-ground ?o ?l))))
    (:action drop-item
     :parameters (?a - agent ?o - object)
     :precondition (and (carrying ?a ?o))
     :effect (when (not (carrying ?a ?o)) (on-ground ?o (location ?a)))
    (:action wake-dragon
     :parameters (?d - dragon)
     :precondition (sleeping ?d)
     :effect (and (awake ?d)))
    (:action fight
     :parameters (?h - hero ?d - dragon)
     :precondition (and (carrying ?h sword-of-fire) (awake ?d))
     :effect (when (not (at ?h village)) (at ?h tower-of-varnak) (not sleeping ?d)))