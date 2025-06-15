(define (problem varnak-adventure)
     (:objects hero sword dragon cave village) ; L'eroe, la spada, il mostro, la grotta e il villaggio
     (:init (and (at hero village) (hidden sword cave) (sleeping dragon))) ; Inizialmente l'eroe si trova nel villaggio, la spada è nascosta nella grotta e il mostro dorme
     (:goal (and (has hero sword) (defeated dragon))) ; L'obiettivo consiste nell'avere la spada e aver sconfitto il mostro
   )