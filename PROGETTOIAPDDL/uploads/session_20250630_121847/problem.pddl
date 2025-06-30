(define (problem dragon-victory)
     (:domain dragon-and-sword)
     (:objects hero village tower-of-varnak ice-dragon sword-of-fire)
     (:init
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon))
     (:goal (and (defeated ice-dragon))))