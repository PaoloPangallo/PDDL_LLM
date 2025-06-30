(define (problem tower-problem)
     (:domain dragon-tower)
     (:objects hero dragon sword-of-fire tower)
     (:init
      (and (at hero village)
           (on-ground sword-of-fire tower)
           (sleeping dragon)
           (awake tower)) )
     (:goal (and (not (alive dragon)))) )