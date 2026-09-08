(define x 1)
(define x (+ x 1))
x
(define (f a b c) (+ a (* b c)))
(f 1 2 3)
(let ((x 10)) (+ x 1) (* x 2))
(let ((s "a\nb")) s)
(define add5 (let ((n 5)) (lambda (y) (+ y n))))
(add5 3)
