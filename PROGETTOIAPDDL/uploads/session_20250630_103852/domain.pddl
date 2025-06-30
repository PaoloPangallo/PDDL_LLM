(define (domain dragon-tower)
     (:requirements :equality :quantifiers :strips :timestamps) ;; Strips is for simplicity, no need to use time in this example
     (:types agent location object dragon hero sword)
     (:predicates
      (at ?x ?loc)
      (on-ground ?o ?loc)
      (carrying ?h ?o)
      (awake ?d)
      (defeated ?d))

     (:action pickup
      :parameters (?h ?o ?l)
      :precondition (and (at ?h ?l) (on-ground ?o ?l))
      :effect (and (not (on-ground ?o ?l)) (carrying ?h ?o)))

     (:action putdown
      :parameters (?h ?o ?l)
      :precondition (and (carrying ?h ?o) (at ?h ?l))
      :effect (and (on-ground ?o ?l) (not (carrying ?h ?o))))

     (:action move
      :parameters (?x ?from ?to)
      :precondition (at ?x ?from)
      :effect (at ?x ?to))

     (:action wake-dragon
      :parameters (?d)
      :precondition (and (on-ground sword-of-fire tower-of-varnak) (at hero tower-of-varnak))
      :effect (awake ice-dragon)))