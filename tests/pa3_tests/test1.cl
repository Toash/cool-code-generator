class Main inherits IO{
    x:Int <- 2;
    main(): Object {
        -- arithmetic
        {
            out_int(2+2);

            out_int(2-3);
            out_int(3-2);

            out_int(2*2);

            out_int(1/10);
            out_int(20/10);
            out_int(15/10);

            out_int(~1);
            out_int(~~2);
            out_int(~~~2);


            out_int(1+~2-3*~4/5);
            out_int(4/~2-~10*~4/5);
            out_int(1+2-3*4/5);
            out_int((1*3)+7);
            out_int(1+(3*7));
            
            out_int(1 + ~(2 * 3) - (4 + ~(5 - ~(6 * ~(7 + 8 / ~(2 + 1)))) * (~(9 + ~(10 - 11))) / 3 + 12 - ~(13 * 2 / ~(~(4 + 1)))));
            out_int(~(~(1 + 2 * ~(3 - ~(4 + ~(5 * 6)))) - (7 * ~(8 + ~(9 - 10))) / (~11 + 12 * ~(~13)) + 14));
            out_int(1 + 2 * (~(3 + ~(4 * ~(5 + 6))) - (7 + ~(8 * (9 - ~(10 + ~(11 / ~(12 - 13))))))));
            out_int((~(1 + ~(2 - 3)) * (4 + ~(5 * ~(6 - ~(7 / ~(8 + 9)))))) + ~(10 * ~(11 + ~(12 - ~(13 + 14)))));
            out_int(~((~(1 + 2) * ~(3 - ~(4 + 5))) - ((6 + ~(7 * ~(8 + 9))) / ~(10 + ~(11 - ~(12 + ~(13 * 14)))))));
            out_int((1 + ~(2 * ~(3 + ~(4 - ~(5 * ~(6 + ~(7 / ~(8 - ~(9 + ~(10 * 11))))))))) - ~(12)));
            out_int(~((1 + ~(2 * ~(3 + ~(4 - ~(5 * ~(6 + ~(7 / ~(8 - ~(9 + ~(10 - ~(11 * ~(12 + 13))))))))))) - ~(14))));
            out_int((~(1 + ~(2 - ~(3 + ~(4 * ~(5 + ~(6 - ~(7 * ~(8 + 9)))))))) + ~(10 / ~(11 + ~(12 * ~(13 - 14))))));
            out_int(~(1 + ~(2 - ~(3 * ~(4 + ~(5 - ~(6 * ~(7 + ~(8 - ~(9 / ~(10 + ~(11 - 12))))))))))));
            out_int((~((1 + ~(2 * ~(3 - ~(4 + ~(5 * ~(6 - ~(7 + ~(8 * ~(9 - ~(10 + ~(11 / ~(12 - 13))))))))))))) + 14));


            out_int(1 + ~(x * 2) - (4 + ~(5 - ~(x * ~(7 + 8 / ~(2 + 1)))) * (~(9 + ~(10 - x))) / 3 + 12 - ~(x * 2 / ~(~(x + 1)))));


            let x : Int<-1 in
            {
                x <- ~x;
                out_int(x);
                x <- ~x;
                out_int(x);
                x <- ~x;
                out_int(x);
                x <- ~x;
                out_int(x);
            };

            
            
        }
    };
};