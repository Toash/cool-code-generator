class Main inherits IO{
    main():Object{
        {
            -- it segfaults on this  :/
            -- out_string(
            --     "".concat("a").concat("b")
            -- );
            out_string("Hello world!\n");
            out_string("Hello world!\n");
            let x:String <- "Hello", y:String <- "Goodbye" in 
            {
                out_string("\n");
                out_int(x.length());
                out_string("\n");
                out_string(x.concat(y));
                out_string("\n");
                out_string(y.substr(0,4));
                out_string("\t");
                out_string(x.substr(1,3));
                out_string("\n");
            };
        }
    };
};