(define (problem quest-dungeon)
     (:domain quest-adventure)
     (:objects hero key treasure chest)
     (:init
      (and (at hero town)
           (in-location key chest)
           (not (in-location treasure chest))) )
     (:goal (and (in-location treasure castle))) )