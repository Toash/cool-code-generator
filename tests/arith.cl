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


            x <- ~x;
            out_int(x);
            x <- ~x;
            out_int(x);
            x <- ~x;
            out_int(x);
            x <- ~x;
            out_int(x);
            
            
        }
    };
};