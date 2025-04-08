echo "Arithmetic test..."
cool --type ./tests/arith.cl
python3 main.py ./tests/arith.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/arith.cl
echo

echo

echo "Assignment test..."
cool --type ./tests/assignment.cl
python3 main.py ./tests/assignment.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/assignment.cl
echo

echo

echo "Bool (no let) test..."
cool --type ./tests/bool_no_let.cl
python3 main.py ./tests/bool_no_let.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/bool_no_let.cl
echo

echo

echo "Let (no init) test..."
cool --type ./tests/let_no_init.cl
python3 main.py ./tests/let_no_init.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/let_no_init.cl
echo

echo

echo "Let (init) test..."
cool --type ./tests/let_init.cl
python3 main.py ./tests/let_init.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/let_init.cl
echo

echo

echo "Unary test..."
cool --type ./tests/unary.cl
python3 main.py ./tests/unary.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/unary.cl
echo

echo

echo "scopes test...."
cool --type ./tests/scopes.cl
python3 main.py ./tests/scopes.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/scopes.cl
echo
echo

echo "PA3c3 test...."
cool --type ./tests/pa3.cl
python3 main.py ./tests/pa3.cl-type
gcc -no-pie -static file.s
./a.out
echo
cool ./tests/pa3.cl
echo


echo

# echo "String test..."
# cool --type ./tests/string.cl
# python3 main.py ./tests/string.cl-type
# gcc -no-pie -static file.s
# ./a.out
# echo
# cool ./tests/string.cl
# echo
